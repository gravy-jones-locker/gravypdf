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

    def test_v_spokes(self):
        self.page.grid.tbls[0].find_v_spokes()
        spokes = self.page.grid.tbls[0].v_spokes
        
        assert spokes[2].lbl.text == 'FY19\n'
        assert spokes[0][0].text == '1.0\n 27.9\n 1.4\n 3.5\n'

    def test_h_spokes(self):
        self.page.grid.tbls[0].find_v_spokes()
        self.page.grid.tbls[0].find_h_spokes()

        spokes = self.page.grid.tbls[0].h_spokes

        assert spokes[3].lbl.text == 'Scope 3 - Business Travel \n'
        assert spokes[1][2].text == '27.9\n'
        assert sum([spokes[2].x0, spokes[2].x1, spokes[2].y0, spokes[2].y1]) == 1143.1673599999997

if __name__ == '__main__':
    unittest.main()