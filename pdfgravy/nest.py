import itertools
import re
import numpy as np
from . import helper
from collections.abc import MutableSequence

class BasePDF:
    @property
    def midx(self):
        return (self.x1 + self.x0) / 2

    @property
    def w(self):  # Width from furthermost left --> right points
        return self.x1 - self.x0

class Nest(MutableSequence, BasePDF):

    """
    Text/edges and other sub (pdfminer) elements are grouped into Nests. These
    behave like mutable sequences, with additional functions/attributes.
    """

    class Decorators:

        @classmethod
        def set_coords(decs, func):
            """
            Resets coordinates of nest based on (new) elements.
            """
            def inner(cls, *args, **kwargs):
                cls = func(cls, *args, **kwargs)
                cls.set_coords()
                return cls            
            return inner

        @classmethod
        def rehome(decs, func):
            """
            Simplifies functions which synthesise new nests from existing items.
            """
            @decs.set_coords
            def inner(cls, *args, **kwargs):
                out = type(cls)()
                for i, elem in enumerate(func(cls, *args, **kwargs)):
                    if kwargs.get('store_parent'):
                        elem.parent = out
                    out.addtwigs(elem)
                return out
            return inner

    def __init__(self, *elems, **kwargs):
        """
        Compile an iterable into a nest for the first time.
        """        
        self._ls = []
        for i, elem in enumerate(elems):
            if kwargs.get('cast'):
            
                if helper.chk_sys_it(elem):
                    elem = type(self)(*elem, **kwargs)  
                elif not isinstance(elem, self.nested):
                    elem = self.nested(elem)

            self.addtwigs(elem)
        
        self.set_coords()

    ####  apply builtins to inner (_ls) list of nested items  ####

    def __len__(self):
        return len(self._ls)

    def __delitem__(self, index):
        self._ls.__delitem__(index)

    def insert(self, index, value):
        self._ls.insert(index, value)

    def __setitem__(self, index, value):
        self._ls.__setitem__(index, value)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self.copy(_ls=self._ls[index])
        return self._ls.__getitem__(index)

    def __iter__(self):
        for obj in self._ls:
            yield obj

    def copy(self, **kwargs):
        """
        Combine stored attrs and modifications in kwargs for new nest.
        """
        out = type(self)()
        for attr in ['parent', 'i', '_ls']:
            v = kwargs[attr] if attr in kwargs else getattr(self, attr, None)
            setattr(out, attr, v)
        return out

    def addtwigs(self, *elems):
        """
        Append new element to sequence and assign index as default.
        """
        for elem in elems:
            elem.i = len(self)
            self._ls.append(elem)

    def agg(self, attr, qnt='median'):
        """
        Returns specified statistical quantity of the specified attribute.
        """
        ref_ls = [getattr(x, attr) for x in self if hasattr(x, attr)]
        if not ref_ls:
            return None        
        return eval(f'np.{qnt}')(ref_ls)

    def set_coords(self):
        """
        Aggregate object coordinates to get new outmost points.
        """
        self.x0 = self.agg('x0', 'min')
        self.x1 = self.agg('x1', 'max')

        self.y0 = self.agg('y0', 'min')
        self.y1 = self.agg('y1', 'max')

    @Decorators.rehome
    def cluster(self, fn, tol=5, reversed=False, store_parent=True):
        """
        Group nested elements by the attribute and function specified.
        """
        ref_ls = []  # Build list of points separated by tolerance
        
        for elem in self:
            if not any([x.clust(elem, fn, tol) for x in ref_ls]):
                ref_ls.append(elem)

        for ref in sorted(ref_ls, key=lambda x: fn(x), reverse=reversed):
            cluster_ls = [x for x in self if x.clust(ref, fn, tol)]
            
            yield type(self)(*cluster_ls)

    @Decorators.rehome
    def denest(self, attr='__len__', flatten=False, cast=False):
        """
        Expose all nested elements according to function specified.
        """
        for elem in self:
            
            if hasattr(elem, attr):
                sub = elem if attr == '__len__' else getattr(elem, attr)
                yield from type(self)(*sub, cast=cast).denest(attr, cast=cast)        
            
            if not hasattr(elem, attr) or not flatten:
                yield elem

    @Decorators.rehome
    def filter(self, fn=None, *args, **filters):
        """
        Return a filtered nest according to the keys/values in the mapping.
        """
        for elem in self:
            if not all([getattr(elem, k, '') == v for k, v in filters.items()]):
                continue
            if fn and not fn(elem, *args):
                continue
        
            yield elem

    def mega_cluster(self, orientation, tol):
        """
        Apply multiple clustering strategies to accommodate alignments.
        """
        if orientation == 'horizontal':
            vars = ['x.x0', 'x.x1', 'x.midx']
        else:
            vars = ['x.y0', 'x.y1', 'x.midy']

        out = type(self)()
        
        for var in vars:
            clusters = self.cluster(lambda x: eval(var), tol)            
            out.addtwigs(*clusters)

        return out

    def apply_nested(self, fn, *args, **kwargs):
        """
        Apply some function to all the nested elements in the nest.
        """
        for i, obj in enumerate(self):
            self[i] = fn(obj, *args, **kwargs)

    def get_sorted(self, fn, i=0, reversed=False):
        """
        Get the indexed element when sorted by the specified function.
        """
        return sorted(self, key=fn, reverse=reversed)[i]

class Nested(BasePDF):

    def __init__(self, elem):
        """
        Store every dictionary value as an attribute of the class instance.
        """
        helper.store_attrs(self, elem)

        if type(elem).__name__.startswith('LT'):
            setattr(self, 'cvttype', type(elem).__name__)

    def clust(self, ref, fn, tol):
        """
        Returns true if the two elements 'clust' - i.e are within clustering.
        """
        val = fn(self)
        ref_val = fn(ref)

        return abs(val - ref_val) <= tol

    def chk_intersection(self, ref):
        """
        Return True if the element is inside the coordinates passed.
        """
        if ref.x0 and self.x1 <= ref.x0 or ref.x1 and self.x0 >= ref.x1:
            return False
        
        if ref.y0 and self.y1 <= ref.y0 or ref.y1 and self.y0 >= ref.y1:
            return False

        return True

    @helper.lazy_property
    def text(self):
        """
        Extract and label text where available.
        """
        if not hasattr(self, 'get_text'):
            self._text = None
        else:
            self._text = self.get_text()

Nest.nested = Nested  # Forward declaration workaround