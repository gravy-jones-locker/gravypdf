from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from .settings import Settings
from .page import Page
from .words import Word, Words
from .nest import Nest
from . import utils
from . import helper
import statistics as stats
import io
import json
from lxml import html

class Pdf:

    """
    Top-level class for access to whole doc attributes/methods.
    """

    def __init__(self, f, user_settings={}):
        """
        Load file as pdf using pdfminer's suite of reading tools.
        """
        self.settings = self.Settings(user_settings)

        self.pages = []
        device, interpreter = utils.init_interpreter()            
        with open(f, 'rb') if isinstance(f, str) else io.BytesIO(f) as stream:  
            self.doc = PDFDocument(PDFParser(stream))
            for i, page in enumerate(PDFPage.create_pages(self.doc)):
                if self.settings['pages'] and i+1 not in self.settings['pages']:
                    continue
                p = Page(page, i+1, device, interpreter)  # +1 = page_no
                self.pages.append(p)

            self.load_info()

    def load_info(self):
        """
        Store bookmark and other helpful information for later use.
        """
        self.info  = self.doc.info
        
        if 'Dests' in self.doc.catalog:
            ds = self.doc.catalog['Dests'].resolve()
            try:
                ds = {k: v.resolve() for k, v in ds.items()}
                self.bmarks = []
                for b in self.doc.get_outlines():
                    self.bmarks.append((b[1], ds[str(b[2]).strip('/\'')]))
            except:
                self.bmarks = []
        else:
            self.bmarks = []

        if 'Metadata' in self.doc.catalog:
            raw = self.doc.catalog['Metadata'].resolve().get_data()
            self.metadata = html.fromstring(raw.decode())
        else:
            self.metadata = ''

    def aggregate_elems(self, attr, parent=Nest):
        """
        Aggregate the elements in the various pages and offset as appropriate.
        """
        off = 0
        out = parent()
        for i, p in enumerate(self.pages[::-1]):
            if p.words and i > 0:
                off -= p.words.get_sorted(lambda x:x.y0).y0
            if p.words:
                ad_off = p.words.get_sorted(lambda x:x.y1, inv=True).y1 + 10
            else:
                ad_off = 0
            if i == 0:
                ad_elems = [x for x in getattr(p, attr)]
            else:
                ad_elems = [x.offset(y=off) for x in getattr(p, attr)]
            
            out.extend(ad_elems)
            off += ad_off

        out.sort(key=lambda x: x.y1, reverse=True)
        out.set_bbox()
        
        return out

    @helper.lazy_property
    def page_h(self):
        self._page_h = stats.median([x.h for x in self.pages])

    @helper.lazy_property
    def page_w(self):
        self._page_w = stats.median([x.w for x in self.pages])

    @helper.lazy_property
    def lines(self):
        self._lines = self.aggregate_elems('lines')

    @helper.lazy_property
    def words(self):
        self._words = self.aggregate_elems('words', Words)

    @helper.lazy_property
    def fonts(self):
        """
        Get stats about fonts from each page then analyse for types.
        """
        fonts = {}
        for page in self.pages:
            page.parse_fonts()
            for fontname, fontstats in page.fonts.items():
                if fontname not in fonts:
                    fonts[fontname] = fontstats
                else:
                    fonts[fontname]["count"] += fontstats["count"] 

        body_count = max([v["count"] for k, v in fonts.items() if not v["bold"] and not v["italic"]])
        for k, v in fonts.items():
            if v["count"] == body_count:
                v["type"] = 'body'
                break

        std_fonts = {k:v for k, v in fonts.items() if not "type" in v}
        sizes = [v["size"] for v in std_fonts.values()]
        sizes.sort(reverse=True)

        body_size = [v["size"] for v in fonts.values() if v.get('type') == 'body'][0]
        
        for k, v in std_fonts.items():
            if v["size"] < body_size:
                fonts[k]["type"] = 'detail'
            else:
                header_no = [i for i, s in enumerate(sizes) if s == v["size"]][0]
                fonts[k]["type"] = f'h{header_no+1}'

        self._fonts = fonts

    def get_headed_sections(self, ref_headers: list):
        """
        Use the reference headers passed to split the pdf into headed sections.
        :param ref_headers: a list of reference values from which to infer
        header spacing and formatting.
        :return: a list of PdfExtract object corresponding to the sections
        found in the pdf.
        """
        lns = self.lines.filter(lambda x:x.orientation == 'h')
        refs = Nest()
        words = self.words.filter(lambda x: not x.marks_p)
        for i, word in enumerate(words):
            if i == len(words) - 1:
                continue
            adj = [words[i-1], words[i+1]]
            chk_lone = not any([abs(x.y0-word.y0) < 5 for x in adj if len(x.text.strip().split(' ')) > 2])
            chk_len  = len(word.text.strip().split(' ')) < 6
            if not chk_lone or not chk_len:
                continue
            word.is_spaced = words[i-1].y0 - word.y1 > 10
            word.is_header = word.text.lower() in ref_headers
            word.is_overlined  = any([0 < x.y1-word.y0 < 5 for x in lns])
            word.is_underlined = any([-5 < x.y1-word.y0 < 0 for x in lns])
            refs.append(word)

        f_refs = refs.cluster(lambda x, y: x.font[1:] == y.font[1:])    
        f_refs = f_refs.filter(lambda x: any([y.is_header for y in x]))
        if len(f_refs) == 0:
            font = ''
        else:
            font = f_refs.get_sorted(lambda x:len(x), inv=True)[0].font

        headers = []
        for i, word in enumerate(refs):
            if word.is_header:
                headers.append(word)
                continue
            chk_font = word.font == font or self.fonts[word.font]['type'] == 'banner'
            if headers and not chk_font:
                prev_words = self.words.filter(lambda x: x.y0 > word.y1 and x.y1 < headers[-1].y0)
                if word.font in set([x.font for x in prev_words]):
                    continue
            if not sum([chk_font, (word.p_break and i != 0), (word.is_spaced and not word.is_overlined), (word.is_underlined and not word.is_spaced)]) > 1:
                continue
            headers.append(word)

        out = []
        for i, header in enumerate(headers):
            if i == len(headers) - 1:
                y0 = 0
            else:
                y0 = headers[i+1].y1
            if i == 0 and self.words.filter(lambda x: x.y0 > y0):
                out.append(PdfExtract(self, self.words.y1 + 10, header.y1, self.words[0]))
            extract = PdfExtract(self, header.y0, y0, header)
            if len(extract.words) > 0:
                out.append(extract)
        for extract in out:
            extract.reset_y_coordinates()
        return [x for x in out if len(x.words) > 0]

    class Settings(Settings):

        defaults = {
            "precision": 0.001,
            "pages": None,
            "headers": None
        }

class PdfExtract:

    def __init__(self, pdf: Pdf, y1: float, y0: float, 
                                                    header: Word=None) -> None:
        """
        Initialise the extract from the elements that fall within its area
        and important info.
        :param pdf: the Pdf object that the extract comes from.
        :param y1: the exact y1 (top) coordinate of the extract.
        :param y0: the exact y0 (bottom) coordinate of the extract.
        :param header: the header at the top of the 
        """
        self.page_w, self.page_h = pdf.page_w, pdf.page_h
        self.fonts = pdf.fonts
        self.words = pdf.words.filter(lambda x: x.y1 < y1 and x.y0 >= y0)
        self.lines = pdf.lines.filter(lambda x: x.y1 < y1 and x.y0 >= y0)
        self.y1 = y1
        self.y0 = y0
        if header != None:
            self.header = header
        else:
            self.header = Word()  # Empty placeholder header

    def reset_y_coordinates(self) -> None:
        """
        Reset the y values of the constituent words, lines etc. to start from 0.
        """
        nests = [self.words, self.lines]
        for nest in nests:
            nest.apply_nested(lambda x: x.offset(y=-self.y0))
            nest.set_bbox()
        if self.header not in self.words:
            self.header.offset(y=-self.y0)