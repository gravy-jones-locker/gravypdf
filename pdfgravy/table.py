from .words import Words
from .nest import Nest, Nested
from . import helper
from .grid import Grid
from .spokes import Spoke, Spokes
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

        self.y0, self.y1 = self.footer.y0, self.header.y1

        # Work down from headers then across from labels for spokes
        self.find_spokes()

    def __repr__(self):
        return f'{self.title}, {self.y1}, {self.y0}'

    def find_spokes(self):
        """
        Find vertical/horizontal spokes from vertical/horizontal labels.
        """
        self.spokes = Spokes()

        # Look from right to left over known vertical (i.e. header) labels
        off_r = self.header.period
        for v_lbl in self.header.lbls[::-1]:

            # Find data - adjusting for offset each iteration
            v_data, off_r = self.get_v_spoke_data(v_lbl, off_r)

            self.spokes.add_vertical(v_lbl, v_data, self.page.words)

        # Use split from vertical data to find horizontal labels
        self.find_h_lbls(self.spokes.agg('x0', 'min'))

        for h_lbl in self.h_lbls[-1]:  # Iterate from hi to lo over inmost
            h_data = Grid(self.page, h_lbl.x1, None, h_lbl.y0, h_lbl.y1).rows

            self.spokes.add_horizontal(h_lbl, h_data, self.h_lbls)

    def get_v_spoke_data(self, hd, off_r):
        """
        Retrieve the data below vertical spokes sorted into sub-spokes.
        """
        mid = hd.midx
            
        # Cut from just after midpoint of label to far right possible col 
        cols_r = Grid(self.page, mid+10, mid+off_r+10, self.y0, hd.y0).cols
        
        off_r = cols_r[-1].agg('midx', 'median') - mid if cols_r else 0

        if off_r < 0:  # True if rightmost col to left of lbl
            cols_l = Nest()
        else:
            # Set righthand limit then look by same amount to left
            if cols_r and cols_r[0].x0 < mid:
                cut_r = cols_r[0].x0  # True if potential overlap
            else:
                cut_r = mid
                
            cols_l = Grid(self.page, mid-off_r, cut_r, self.y0, hd.y0).cols

        return Nest(*cols_r, *cols_l), off_r

    def find_h_lbls(self, lbl_cut):
        """
        Given an x cut between labels/data find row labels.
        """
        self.h_lbls = Nest()

        lbl_grid = Grid(self.page, None, lbl_cut, self.y0, self.y1)

        for col in sorted(lbl_grid.cols, key=lambda x: x.x0):
            col_lbls = lbl_grid.segment_col(col)  # Split each col into rows
            col_lbls = col_lbls.filter(lambda x: x)

            self.h_lbls.append(col_lbls)

        self.h_lbls.set_bbox()
        self.h_lbls.apply_nested(Nest.set_bbox, x_only=True)

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