import unittest
import pdfgravy

class ConstructorClass:
    @classmethod
    def setUpClass(cls):
        cls.pdf  = pdfgravy.pdf.PDF(cls.PATH)
        cls.page = cls.pdf.pages[0]
        
        _ = cls.page.objects  # Necessary to load 'lazy' _objects property

    @classmethod
    def tearDownClass(cls):
        cls.pdf.stream.close()

class BaseTest(ConstructorClass, unittest.TestCase):
    def test_word_extraction(self):
        words = self.page.words
        assert len(words) == self.results['word_extraction']

class BaseTableTest(ConstructorClass, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.page.grid = pdfgravy.page.PageGrid(cls.page, {})
        cls.page.grid.split()

    def test_split(self):       
        assert repr(self.page.grid.tbls[0]) == self.results['split'][0]

    def test_v_spokes(self):
        self.page.grid.tbls[0].find_v_spokes()
        spokes = self.page.grid.tbls[0].spokes
        
        assert spokes[2].lbl.text == self.results['v_spokes'][0]
        assert spokes[0][0].text == self.results['v_spokes'][1]

    def test_h_spokes(self):
        self.page.grid.tbls[0].find_lbls()
        self.page.grid.tbls[0].find_h_spokes()

        spokes = self.page.grid.tbls[0].spokes

        assert spokes[3].lbl.text == self.results['h_spokes'][0]
        assert spokes[1][2].text == self.results['h_spokes'][1]

    def test_lbls(self):
        self.page.grid.tbls[0].find_lbls()

        assert 1 == self.results['lbls']