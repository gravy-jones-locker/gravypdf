from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from .settings import Settings
from .page import Page
from . import utils

class PDF:

    """
    Top-level class for access to whole doc attributes/methods.
    """

    def __init__(self, fpath, user_settings={}):
        """
        Load file as pdf using pdfminer's suite of reading tools.
        """
        self.settings = self.Settings(user_settings)

        self.pages = []
        device, interpreter = utils.init_interpreter()
        with open(fpath, 'rb') as stream:     
            doc = PDFDocument(PDFParser(stream))       
            for i, page in enumerate(PDFPage.create_pages(doc)):
                if self.settings['pages'] and i+1 not in self.settings['pages']:
                    continue
                p = Page(page, i+1, device, interpreter)  # +1 = page_no
                self.pages.append(p)

    class Settings(Settings):

        defaults = {
            "precision": 0.001,
            "pages": None,
        }