from .grid import Grid
from .words import Words
from .nest import Nest

class Table(Grid):

    def __init__(self, page, hi, lo, title):
        """
        Store essential info and cut elements from page.
        """
        super().__init__(page, y1=hi.agg('y1', 'max'), y0=lo.agg('y0', 'min'))
        
        self.header = hi
        self.footer = lo

        self.title = title.strip('\n \r')

    def __repr__(self):
        return f'{self.title}, {self.y0}, {self.y1}'

    def find_v_spokes(self):
        """
        Find the columns of data which extend from each label in the top header
        row.
        """
        self.v_spokes = Nest()

        off_l = 0
        for lbl in self.header.lbls[::-1]:  # Iterate r --> l over known labels
            
            # Split the grid to below/right of label and look for word cols
            xr = lbl.midx + self.header.period - off_l
            r = self.get_sub(x0=lbl.midx, x1=xr, y0=self.y0, y1=lbl.y0)
            
            # Then look to the left by a corresponding amount
            off_l = self.get_lbl_off(lbl, r.w_cols, self.header.period, 'midx')
            
            xl = lbl.midx - self.header.period + off_l
            l = self.get_sub(x0=xl, x1=lbl.midx, y0=self.y0, y1=lbl.y0)

            self.v_spokes.addtwigs(Spoke(lbl, *l.w_cols, *r.w_cols))

    def find_h_spokes(self):
        """
        Find and label the horizontal spokes from the position of the values.
        """
        self.h_spokes = Nest()

        col_l = self.v_spokes[-1].get_sorted(lambda x: x.x0)

        for val in col_l:  # Find closest horizontal label
            sub = self.get_sub(x0=self.x0, x1=self.x1, y0=val.y0, y1=val.y1)
            if len(sub.w_cols) < len(self.header.lbls):
                continue  # Ignore any without the full complement of values
            
            lbls, data = sub.w_cols.split(lambda x: x.x0 < col_l.x0)
            lbl = lbls.get_sorted(lambda x: abs(x.x1 - col_l.x0))  

            self.h_spokes.addtwigs(Spoke(lbl, *data))

    def get_sub(self, x0, x1, y0, y1):
        """
        Plot the columns of data which follow down from a label.
        """
        sub = Grid(self.page, x0=x0, x1=x1, y0=y0, y1=y1)
        sub.find_w_cols(5)

        return sub

    def get_lbl_off(self, lbl, data, period, attr):
        """
        Get the offset of the data attached to the label from the expected pos.
        """
        if len(data) == 0:  # If no data found return full period
            return period
        else:
            return lbl.midx + period - data[-1].agg(attr, 'median')

class Spoke(Nest):

    def __init__(self, lbl, *clusters):
        """
        Store constitutive spoke and label data. 
        """
        self.lbl  = lbl
        self.title = lbl.text
        
        super().__init__(*clusters)