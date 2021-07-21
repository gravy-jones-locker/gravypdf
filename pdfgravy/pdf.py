from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from .settings import Settings
from .page import Page
from .words import Words
from .nest import Nest
from . import utils
from . import helper
import statistics as stats
import io

class PDF:

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

    def aggregate_elems(self, attr, parent=Nest):
        """
        Aggregate the elements in the various pages and offset as appropriate.
        """
        off = 0
        out = parent()
        for i, p in enumerate(self.pages[::-1]):
            if i == 0:
                ad_elems = [x for x in getattr(p, attr)]
            else:
                ad_elems = [x.offset(y=off) for x in getattr(p, attr)]
            
            out.extend(ad_elems)
            if p.words:
                off += p.words.get_sorted(lambda x:x.y1, inv=True).y1 + 10
            else:
                off += 0

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
    def headers(self):
        """
        Find obvious top-level headers using any keywords passed.
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
            word.is_header = word.text.lower() in self.settings["headers"]
            word.is_lined  = any([abs(x.y1-word.y0) < 5 for x in lns]) 
            refs.append(word)

        f_refs = refs.cluster(lambda x, y: x.font[1:] == y.font[1:])    
        f_refs = f_refs.filter(lambda x: any([y.is_header for y in x]))
        font   = f_refs.get_sorted(lambda x:len(x), inv=True)[0].font

        self._headers = Words()
        for word in refs:
            if word.is_header:
                self._headers.append(word)
                continue
            chk_font = word.font == font
            if self._headers and not chk_font:
                prev_words = self.words.filter(lambda x: x.y0 > word.y1 and x.y1 < self._headers[-1].y0)
                if word.font in set([x.font for x in prev_words]):
                    continue
            if not sum([chk_font, word.is_spaced, word.is_lined]) > 1:
                continue
            self._headers.append(word)
        self._headers.set_bbox()

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

    class Settings(Settings):

        defaults = {
            "precision": 0.001,
            "pages": None,
            "headers": None
        }