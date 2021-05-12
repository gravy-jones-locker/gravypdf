import unittest
import pdfgravy
from tests.test_main import BaseTest

class TableTest(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.page.grid = pdfgravy.page.PageGrid(cls.page, {})
        cls.page.grid.split()

    def test_split(self):       
        assert repr(self.page.grid.tbls[0]) == 'Greenhouse Gas Emissions Normalized by Revenue (mtCO2e/M$), 76.494, 144.53'
        assert repr(self.page.grid.tbls[1]) == 'Greenhouse Gas Emissions (mtCO2e), 317.0, 565.57'

    def test_edges(self):
        self.page.grid.tbls[0].find_v_spokes()
        assert 1 == 1

if __name__ == '__main__':
    unittest.main()