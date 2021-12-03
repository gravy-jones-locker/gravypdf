from .nest import Nest, Nested
from .table import Table
from .words import Word, Words, Header
from . import helper
import numpy as np

class Page:

    """
    Access to page-level operations all conducted through this class.
    """

    def __init__(self, page_obj, page_no, device, interpreter):
        """
        Store important info from the pdfminer page object.
        """
        self.page_no  = page_no
        self.rotation = page_obj.attrs.get("Rotate", 0) % 360

        self.w, self.h = page_obj.mediabox[2:]

        # Use pdfminer API to load precise layout of elements on page
        interpreter.process_page(page_obj)
        layout = device.get_result()

        objects = Nest(*layout._objs, cast=True).denest('_objs', cast=True)
        self.objects = objects.filter(lambda x:x.cvttype in [
                                                'LTLine',
                                                'LTRect',
                                                'LTTextBoxHorizontal',
                                                'LTTextLineHorizontal',
                                                'LTChar'
                                                ])
        self.chars = self.get_chars()
        self.text  = self.get_text()
        self.words = self.get_words()
        self.lines = self.get_lines()
        self.boxes = self.get_boxes()

    def extract_tables(self, user_settings={}):
        """
        Divide the page into tables and extract the data therein.
        """
        self.tbls = {}

        settings = Table.Settings(user_settings)
        
        if settings['header_pattern']:            
            self.split_by_headers(settings['header_pattern'])
        if settings['remove_whitespace']:
            self.words.apply_nested(lambda x: x.rm_wspace())

        for i, (header, footer, title) in enumerate(self.tbls.values()):
            self.tbls[i] = Table(self, header, footer, title, settings)

        return self.tbls

    def split_by_headers(self, pattern):
        """
        Use header info to isolate coordinates of tables in page.
        """
        rows = self.words.cluster(lambda x: x.y1)

        header_rows = {}
        for i, row in enumerate(rows):
            score = row.score_incidence(pattern, True)

            if score > 2:  # True if header pattern reappears consecutively
                header_rows[len(header_rows)] = Header(row, pattern)

        for i, row in header_rows.items():
            prev = header_rows[i - 1] if i > 0 else rows[0]
            
            self.tbls[i] = row.cvt_header2tbl(prev, rows)

    def segment(self, y_gap=10, x_gap=10):
        """
        Split the page into segments based on the spacing of text lines.
        """
        segs  = self.words.negative_cluster(y_gap, x_gap)
        lines = self.lines.filter(lambda x: x.orientation == 'h') 

        testLn = lambda x, y: x.chk_intersection(y)# and y.w >= 0.7 * x.w
        out = []
        for i, seg in enumerate(segs):
            if len(seg) == 1 and i < len(segs) - 1:
                segs[i+1].insert(0, seg[0])
                continue
            xls = [x for x in lines if testLn(seg, x)]
            if not xls and seg:
                out.append(seg)
            elif seg:
                xls.sort(key=lambda x:x.y1, reverse=True)
                lo = seg
                for ln in xls:
                    hi, lo = lo.split(lambda x: x.y0 > ln.y1 + 5)
                    if hi:
                        out.append(hi)
                if lo:
                    out.append(lo)
        
        return Words(*[x for x in out if x])

    def parse_fonts(self):
        """
        Identify which fonts in the page are headers etc.
        """
        fs = set([x.font for x in self.words])

        fonts = {}
        for font in fs:
            if not font:
                continue
            ws = self.words.filter(lambda x: x.font == font)
            if not ws:
                continue
            fonts[font] = {}
            fonts[font]["count"] = len([x for y in ws for x in y])
            try:
                fonts[font]["size"]  = int(font.split('_')[1])
            except:
                fonts[font]["size"] = 4  # TODO improve
            fonts[font]["bold"] = 'Bold' in font
            fonts[font]["italic"] = 'Italic' in font
            fonts[font]["top_only"] = ws.y0 > 500

        for k, f in fonts.items():
            if self.page_no == 1 and f["top_only"] and f["size"] >= 16:
                fonts[k]["type"] = "banner"
        
        self.fonts = fonts

    ####  objects from pdf layer evaluated then stored on-demand/lazily  ####

    def get_lines(self):
        lines = self.objects.filter_attrs(cvttype='LTLine')
        rects = self.objects.filter_attrs(cvttype='LTRect')
        
        rects.apply_nested(Nested.get_coords_from_bbox)
        
        rects_v = rects.filter(lambda x: x.x1 - x.x0 < 3)
        rects_h = rects.filter(lambda x: x.y1 - x.y0 < 3)

        rects_v.apply_nested(Nested.squash, 'x')
        rects_h.apply_nested(Nested.squash, 'y')
        
        lines = Nest(*lines, *rects_v, *rects_h)
        lines.sort(key=lambda x:x.y0)
        for i, ln in enumerate(lines):
            if not hasattr(ln, 'x0'):
                lines[i].x0 = 0
            if not hasattr(ln, 'y0'):
                lines[i].y0 = 0
        return lines

    def get_chars(self):
        return self.objects.filter_attrs(cvttype='LTChar')

    def get_text(self):
        return self.objects.filter_attrs(cvttype='LTTextLineHorizontal')

    def get_boxes(self):
        return self.objects.filter_attrs(cvttype='LTTextBoxHorizontal')

    def get_words(self):
        ws = Words(*[Word(*x._objs, cast=True) for x in self.text], cast=True)
        ws.sort(key=lambda x: x.y1, reverse=True)
        words = ws.clean()
        words = words.split_fonts().filter(Word.test_alphanum)
        words.lbl_ends()
        return words.filter(lambda x: not x.marks_p)