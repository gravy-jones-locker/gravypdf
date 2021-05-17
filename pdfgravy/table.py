from .words import Words
from .nest import Nest, Nested
from . import helper
from .grid import Grid
from .spoke import Spoke
from .settings import Settings

class Table:

    def __init__(self, page, header, footer, title, settings):
        """
        Every table is immediately plotted on creation of the instance.
        """
        self.header = header
        self.footer = footer
        self.settings = settings
        
        self.page = page
        self.title = title.strip('\n \r')

        self.grid = Grid(page, settings, y0=self.footer.y0, y1=self.header.y1)
        
        self.spokes = Nest()

        self.find_v_spokes()  # Work down from headers for v spokes
        self.find_h_spokes()  # Work across from labels for h spokes

    def __repr__(self):
        return f'{self.title}, {self.grid.y0}, {self.grid.y1}'

    def find_v_spokes(self, off_r=0):
        """
        Find the columns of data which extend from each label in the top header
        row.
        """
        for lbl in self.header.lbls[::-1]:  # Iterate r --> l over known labels

            # Find any columns to the right of the current label
            xr = lbl.midx + self.header.period - off_r
            cols_r = self.grid.cols.slice(x0=lbl.midx, x1=xr)

            if cols_r:  # Calculate the offset to the data from the expected pt
                col_rmost = cols_r[-1]
                off_r = col_rmost.agg('midx', 'median') - lbl.midx

            # Do the same to the left, applying the offset found
            xl = lbl.midx - self.header.period + off_r

            if cols_r and xl < col_rmost.x0:
                cols_l = self.grid.cols.slice(x0=xl, x1=col_rmost.x0)
            elif not cols_r:
                cols_l = self.grid.cols.slice(x0=xl, x1=lbl.midx)
            else:
                cols_l = Nest()
                
            # Initialise top-level spoke from all columns found under the header
            # and split by sub-headers, if found.

            spokes = Spoke(lbl, *cols_l, *cols_r).split_v()

            self.spokes.addtwigs(*spokes)

    def find_h_spokes(self):
        """
        Find and label the horizontal spokes from the position of the values.
        """
        lbls = Nest()

        # From the non-data area of the grid get the label of each row  
        lbl_cut = self.header.lbls[0].midx - self.header.period
        lbl_cols = self.grid.cols.slice(x1=lbl_cut)

        for col in lbl_cols[::-1]:
            col_lbls = self.grid.segment_col(col)  # Split each col into rows
            
            lbls.append(col_lbls)

        # Once found derive horizontal spokes from row labels + their position
        inner = lbls.get_sorted(lambda x: x.x0, inv=True)

        for lbl in inner:
            cols = self.grid.cols.slice(x0=lbl.x0, y0=lbl.y0, y1=lbl.y1)
            
            if len(cols) < len(self.header.lbls):
                continue  # Ignore any without the full compliment of values  
            
            # Consolidate the data found according to aggregate labels etc. 
            spokes = Spoke(lbl, *cols).consolidate_h(lbls)
            
            self.spokes.addtwigs(spokes)

    class Settings(Settings):

        defaults = {
            "explicit_vertical_lines": [],
            "explicit_horizontal_lines": [],
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 3,
            "min_words_vertical": 3,
            'min_words_vertical_ratio': 0.5,
            "min_words_horizontal": 1,
            "intersection_tolerance": 3,
            "intersection_x_tolerance": None,
            "intersection_y_tolerance": None,
            "find_headers": True,
            "header_pattern": [r'(?:20|FY|fy)(\d\d)']
        }

        fallbacks = {
            "intersection_x_tolerance": "intersection_tolerance",
            "intersection_y_tolerance": "intersection_tolerance"
        }