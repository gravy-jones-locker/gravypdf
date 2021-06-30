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
        self.layout = device.get_result()

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

    def segment_by_line(self, y_gap=10, x_gap=10):
        """
        Split the page into segments based on the spacing of text lines.
        """
        return self.words.negative_cluster(y_gap, x_gap)

    ####  objects from pdf layer evaluated then stored on-demand/lazily  ####

    @helper.lazy_property
    def objects(self):
        self._objects = Nest(*self.layout._objs, cast=True)
        self._objects = self._objects.denest('_objs', cast=True)

    @helper.lazy_property
    def lines(self):
        lines = self.objects.filter_attrs(cvttype='LTLine')
        rects = self.objects.filter_attrs(cvttype='LTRect')
        
        rects_v = rects.filter(lambda x: x.x1 - x.x0 < 3)
        rects_h = rects.filter(lambda x: x.y1 - x.y0 < 3)

        rects_v.apply_nested(Nested.squash, 'x')
        rects_h.apply_nested(Nested.squash, 'y')
        
        self._lines = Nest(*lines, *rects_v, *rects_h)

        self._lines.sort(key=lambda x:x.y0)

    @helper.lazy_property
    def chars(self):
        self._chars = self.objects.filter_attrs(cvttype='LTChar')

    @helper.lazy_property
    def text(self):
        self._text = self.objects.filter_attrs(cvttype='LTTextLineHorizontal')

    @helper.lazy_property
    def words(self):
        ws = Words(*[Word(*x._objs, cast=True) for x in self.text], cast=True)
        self._words = ws.filter(Word.has_txt)