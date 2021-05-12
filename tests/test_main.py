import unittest
import pdfgravy

class BaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pdf  = pdfgravy.pdf.PDF('tests/pdfs/msft.pdf')
        cls.page = cls.pdf.pages[0]
        
        _ = cls.page.objects  # Necessary to load 'lazy' _objects property

    @classmethod
    def tearDownClass(cls):
        cls.pdf.stream.close()


class Test(BaseTest):
    def test_load(self):
        assert len(self.pdf.pages) == 1
    
    def test_word_extraction(self):
        words = self.page.words
        assert len(words) == 104

if __name__ == '__main__':
    unittest.main()