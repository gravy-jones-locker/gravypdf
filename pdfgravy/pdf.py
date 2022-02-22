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
            doc = PDFDocument(PDFParser(stream))
            for i, page in enumerate(PDFPage.create_pages(doc)):
                if self.settings['pages'] and i+1 not in self.settings['pages']:
                    continue
                p = Page(page, i+1, device, interpreter)  # +1 = page_no
                self.pages.append(p)

            self.load_info(doc)

        self.lines = self.get_lines()
        self.words = self.get_words()
        self.fonts = self.get_fonts()

    def load_info(self, doc):
        """
        Store bookmark and other helpful information for later use.
        """
        self.info  = doc.info
        
        if 'Dests' in doc.catalog:
            ds = doc.catalog['Dests'].resolve()
            try:
                ds = {k: v.resolve() for k, v in ds.items()}
                self.bmarks = []
                for b in doc.get_outlines():
                    self.bmarks.append((b[1], ds[str(b[2]).strip('/\'')]))
            except:
                self.bmarks = []
        else:
            self.bmarks = []

        if 'Metadata' in doc.catalog:
            raw = doc.catalog['Metadata'].resolve().get_data()
            self.metadata_bytes = raw.decode()
        else:
            self.metadata_bytes = b''

    def aggregate_elems(self, attr, parent=Nest):
        """
        Aggregate the elements in the various pages and offset as appropriate.
        """
        off = 0
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
            if i == 0:
                out = parent(*ad_elems)
            else:
                out = parent(*ad_elems, *out)
            off += ad_off

        out.set_bbox()
        
        return out

    @helper.lazy_property
    def page_h(self):
        self._page_h = stats.median([x.h for x in self.pages])

    @helper.lazy_property
    def page_w(self):
        self._page_w = stats.median([x.w for x in self.pages])

    def get_lines(self):
        return self.aggregate_elems('lines')

    def get_words(self):
        return self.aggregate_elems('words', Words)

    def get_fonts(self):
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

        return fonts

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
            word.is_spaced = words[i-1].y0 - word.y1 > 10 and (words[i+1].x0 - word.x1 > 15 or word.y0 - words[i+1].y1 > 0)
            word.is_header = word.text.lower() in ref_headers
            word.is_overlined  = any([0 < x.y1-word.y1 < 10 for x in lns])
            word.is_underlined = any([-10 < x.y1-word.y0 < 5 for x in lns])
            refs.append(word)

        f_refs = refs.cluster(lambda x, y: x.font == y.font and x.is_underlined == y.is_underlined)    
        f_refs = f_refs.filter(lambda x: any([y.is_header for y in x]))
        if len(f_refs) == 0:
            font = ''
        else:
            f_refs.sort(key=lambda x: len(x), reverse=True)
            font = f_refs.get_sorted(lambda x:len([y for y in x if y.is_header]), inv=True)[0].font

        headers = []
        for i, word in enumerate(refs):
            if word.is_header:
                headers.append(word)
                continue
            chk_font = word.font == font or self.fonts[word.font]['type'] == 'banner'
            chk_font = chk_font or ('Bold' in font and font[1:-2] == word.font[1:-2] and self.fonts[font]["size"]) - self.fonts[word.font]["size"] < 2
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
            if i == 0:
                ws = self.words.filter(lambda x: x.y0 > header.y1)
                if ws:
                    out.append(self.extract(self, self.words.y1 + 10, header.y1, self.words[0]))
            if i == 0 and len(out) == 0 and header.text.lower() not in ref_headers:
                extract = self.extract(self, self.words.y1 + 10, y0, header)
                if len(extract.words) == 1 and extract.words[0] == header:
                    continue
            else:
                extract = self.extract(self, header.y0, y0, header)
            if len(extract.words) > 0:
                out.append(extract)
        #for extract in out:
            #extract.reset_y_coordinates()
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
        self._pdf = pdf
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
            nest.set_bbox()

Pdf.extract = PdfExtract