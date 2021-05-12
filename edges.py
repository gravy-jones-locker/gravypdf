from nest import Nest, Nested

class Edges(Nest):

    pass

class Edge(Nested):

    def __init__(self, elem):
        """
        Calculate line orientation on construction.
        """
        super().__init__(elem)

        self.h = self.y0 == self.y1
        self.v = not self.h

Edges.nested = Edge  # Forward declaration workaround