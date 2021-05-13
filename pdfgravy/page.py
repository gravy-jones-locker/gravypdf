from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from .nest import Nest
from .edges import Edges
from .table import Table
from .grid import Grid
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
        self.grid = PageGrid(self, user_settings)
        self.grid.split()

        self.grid.fill()

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
        self._lines = Edges(*self.objects.filter(cvttype='LTLine'), cast=True)

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

class PageGrid(Grid):

    """
    Uses edge/word-location info to split page into subgrids prior to table
    extraction.
    """

    def __init__(self, page, user_settings):
        """
        Configure settings and extract info from page.
        """
        super().__init__(page)
        
        self.settings = self.Settings(user_settings)

    def split(self):
        """
        Split grid into tables via chosen splitting method.
        """
        self.tbls = {}

        if self.settings['header_pattern']:            
            self.split_by_headers()
    
    def split_by_headers(self):
        """
        Use header info to isolate coordinates of tables in page.
        """
        self.rows = self.words.cluster(lambda x: x.y1)

        header_rows = {}
        for i, row in enumerate(self.rows):
            pattern = self.settings['header_pattern']
            score = row.score_incidence(pattern, True)

            if score > 2:  # True if header pattern reappears consecutively
                header_rows[len(header_rows)] = Header(row, pattern)

        for i, row in header_rows.items():
            prev = header_rows[i - 1] if i > 0 else self.rows[0]
            
            self.tbls[i] = Table(*row.cvt_header2tbl(prev, self.page))

    def fill(self):
        """
        Fill out the tables in the pagegrid from word/edge patterns.
        """
        for tbl in self.tbls.values():
            tbl.words.apply_nested(lambda x: x.rm_wspace())

            tbl.find_lbls()
            
            tbl.find_v_spokes()  # Work down from headers for vertical spokes
            tbl.find_h_spokes()  # Work across from labels for horiz spokes