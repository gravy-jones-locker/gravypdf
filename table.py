from grid import Grid

class Table(Grid):

    def __init__(self, page, y1, y0, title):
        """
        Store essential info and cut elements from page.
        """
        self.y1 = y1  # hi/++ --> higher
        self.y0 = y0  # lo/-- --> lower

        self.title = title

        self.words = self.fit_grid(page.words)
        self.edges = self.fit_grid(page.edges)

    def fill_edges(self):
        """
        Use word-based and pdf edge data to build up the grid edges. 
        """
        pass

    def plot_cells(self):
        pass