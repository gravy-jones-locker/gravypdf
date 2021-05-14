from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.layout import LAParams

from .settings import Settings
from .page import Page

class PDF:

    """
    Top-level PDF class mainly stores relevant pdfminer classes and does
    initial page load.
    """

    def __init__(self, fpath, user_settings={}):
        """
        Load file as pdf using pdfminer's suite of reading tools.
        """
        self.settings = self.Settings(user_settings)

        self.laparam = LAParams(char_margin=1)
        self.rsrcmgr  = PDFResourceManager()

        self.stream = open(fpath, 'rb')
        self.doc = PDFDocument(PDFParser(self.stream))
            
        self.load_pages()  # Read stream while file open
    
    def load_pages(self):
        """
        Load pages into memory as list of page objects.
        """
        self.pages = []
        for i, page in enumerate(PDFPage.create_pages(self.doc)):
            if self.settings['pages'] and i + 1 not in self.settings['pages']:
                continue
            p = Page(self, page, i + 1)  # Add 1 to index to get page_no
            self.pages.append(p)        

    class Settings(Settings):

        defaults = {
            "precision": 0.001,
            "pages": None
        }