import pdfgravy
from tests.test_base import BaseTest, BaseTableTest

class Msft1(BaseTest):
    PATH = 'tests/pdfs/msft.pdf'

    results = {
        'word_extraction': 104
    }

class Msft1Table(BaseTableTest):
    PATH = Msft1.PATH
    
    results = {

        'split': ('Greenhouse Gas Emissions Normalized by Revenue (mtCO2e/M$), 76.494, 144.53',),
        
        'v_spokes': ('FY19\n', '1.0\n 27.9\n 1.4\n 3.5\n'),

        'h_spokes': ('Scope 3 - Business Travel \n', '26.7\n', 798.3373599999999),

        'lbls': 1
    }

class Apple65(BaseTest):
    PATH = 'tests/pdfs/apple_65.pdf'
    
    results = {
        'word_extraction': 169
    }

class Apple65Table(BaseTableTest):
    PATH = Apple65.PATH

    results = {

        'split': ('Energy, 112.6329, 650.6102999999999',),
        
        'v_spokes': ('2017\n', '996\n 831\n 166\n  105,940 \n  143,660 \n  70 \n  37,875,000 \n  167,670 \n  38,815,530 \n  - \n 336,000\n  - \n  - \n  - \n 920\n 93%\n  - \n  - \n  - \n'),

        'h_spokes': ('MWh\n', '351\n', 1897.0295),

        'lbls': 1
    }