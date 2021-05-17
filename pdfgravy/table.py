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

        self.y0, self.y1 = self.footer.y0, self.header.y1
        
        self.page = page
        self.title = title.strip('\n \r')
        
        self.spokes = Nest()

        self.find_v_spokes()  # Work down from headers for v spokes
        self.find_h_spokes()  # Work across from labels for h spokes

        pass

    def __repr__(self):
        return f'{self.title}, {self.y1}, {self.y0}'

    def find_v_spokes(self):
        """
        Find the columns of data which extend from each label in the top header
        row.
        """
        off_r = self.header.period * 0.8

        for lbl in self.header.lbls[::-1]:  # Iterate r --> l over known labels

            # Find any columns to the right of the current label
            xr = lbl.midx + off_r
            cols_r = Grid(self.page, lbl.midx, xr, self.y0, self.y1).cols

            if cols_r:  # Calculate the offset to the data from the expected pt
                rmost = cols_r[-1]
                off_r = rmost.agg('midx', 'median') - lbl.midx

            # Do the same to the left, applying the offset found
            xl = lbl.midx - off_r

            if cols_r and xl < rmost.x0:
                cols_l = Grid(self.page, xl, rmost.x0, self.y0, self.y1).cols
            elif not cols_r:
                cols_l = Grid(self.page, xl, lbl.midx, self.y0, self.y1).cols
            else:
                cols_l = Nest()
                
            # Initialise top-level spoke from all columns found under the header
            # and split by sub-headers, if found.

            spokes = Spoke([lbl], *cols_l, *cols_r).split_v()

            self.spokes.addtwigs(*spokes)

    def find_h_spokes(self):
        """
        Find and label the horizontal spokes from the position of the values.
        """
        lbls = Nest()

        # From the non-data area of the grid get the label of each row  
        lbl_cut = self.header.lbls[0].midx - self.header.period
        lbl_grid = Grid(self.page, None, lbl_cut, self.y0, self.y1)

        for col in sorted(lbl_grid.cols, key=lambda x: x.x0):
            col_lbls = lbl_grid.segment_col(col)  # Split each col into rows
            
            lbls.append(col_lbls)
        
        lbls.apply_nested(Nest.set_coords)
        flat_lbls = Nest(*[x for y in lbls for x in y])

        # Once found derive horizontal spokes from row labels + their position
        for lbl in lbls[-1]:
            rows = Grid(self.page, lbl.x1, None, lbl.y0, lbl.y1).rows 
            
            # Consolidate the data found according to aggregate labels etc. 
            spokes = Spoke([lbl], *rows).consolidate_h(flat_lbls)
            
            self.spokes.addtwigs(*spokes)

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
            "header_pattern": [r'(?:20|FY|fy)(\d\d)'],
            "word_tolerance_vertical": 5,
            "word_tolerance_horizontal": 5,
            "remove_whitespace": True
        }

        fallbacks = {
            "intersection_x_tolerance": "intersection_tolerance",
            "intersection_y_tolerance": "intersection_tolerance"
        }