from .grid import Grid

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
        Find the vertical spokes down from each header.
        """
        cut_r = 0
        for lbl in self.header.lbls(True):  # Iterate l <-- r over known labels
            x1 = lbl.midx + self.header.period * 0.8 - cut_r
            
            sub = Grid(self.page, x0=lbl.midx, x1=x1, y1=lbl.y0, y0=self.y0)
            sub.find_word_cols(5)
            
            pass       

    def plot_cells(self):
        pass