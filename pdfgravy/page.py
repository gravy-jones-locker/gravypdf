from pdfgravy.settings import Settings
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from .nest import Nest, Nested
from .edges import Edges
from .table import Table
from .words import Word, Words, Header
from . import helper

class Page:

    """
    Access to page-level operations all conducted through this class.
    """

    def __init__(self, pdf, page_obj, page_no):
        """
        Store important info from the pdfminer page object.
        """
        self.page_obj = page_obj
        self.pdf = pdf

        self.page_no  = page_no
        self.rotation = page_obj.attrs.get("Rotate", 0) % 360

        self.w, self.h = page_obj.mediabox[2:]

    def extract_tables(self, user_settings={}):
        """
        Divide the page into tables and extract the data therein.
        """
        self.tbls = {}

        settings = Table.Settings(user_settings)
        
        if settings['header_pattern']:            
            self.split_by_headers()
        if settings['remove_whitespace']:
            self.words.apply_nested(lambda x: x.rm_wspace())

        for i, (header, footer, title) in enumerate(self.tbls.values()):
            self.tbls[i] = Table(self, header, footer, title, settings)

        return self.tbls

    def split_by_headers(self):
        """
        Use header info to isolate coordinates of tables in page.
        """
        rows = self.words.cluster(lambda x: x.y1)
        pattern = self.settings['header_pattern']

        header_rows = {}
        for i, row in enumerate(rows):
            score = row.score_incidence(pattern, True)

            if score > 2:  # True if header pattern reappears consecutively
                header_rows[len(header_rows)] = Header(row, pattern)

        for i, row in header_rows.items():
            prev = header_rows[i - 1] if i > 0 else rows[0]
            
            return row.cvt_header2tbl(prev, rows)

    ####  objects from pdf layer evaluated then stored on-demand/lazily  ####
        
    @helper.lazy_property
    def layout(self):
        """
        Use pdfminer device/interpreter logic to get layout.
        """
        device = PDFPageAggregator(self.pdf.rsrcmgr, laparams=self.pdf.laparam)
        interpreter = PDFPageInterpreter(self.pdf.rsrcmgr, device)
    
        interpreter.process_page(self.page_obj)
        self._layout = device.get_result()

    @helper.lazy_property
    def objects(self):
        self._objects = Nest(*self.layout._objs, cast=True)
        self._objects = self._objects.denest('_objs', cast=True)

    @helper.lazy_property
    def lines(self):
        self._lines = Nest(*self.objects.filter(cvttype='LTLine'), cast=True)
        self._lines.apply_nested(Nested.calc_orientation)

    @helper.lazy_property
    def chars(self):
        self._chars = self.objects.filter(cvttype='LTChar')

    @helper.lazy_property
    def text(self):
        self._text = self.objects.filter(cvttype='LTTextLineHorizontal')

    @helper.lazy_property
    def words(self):
        ws = Words(*[Word(*x._objs, cast=True) for x in self.text], cast=True)
        self._words = ws.filter(Word.has_txt)