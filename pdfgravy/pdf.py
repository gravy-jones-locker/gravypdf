from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from .settings import Settings
from .page import Page
from . import utils
from . import helper

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

    @helper.lazy_property
    def fonts(self):
        """
        Get stats about fonts from each page then analyse for types.
        """
        fonts = {}
        for page in self.pages:
            page.parse_fonts()
            for font in [f for f in page.fonts if f not in fonts]:
                fonts[font] = page.fonts[font]

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
        }