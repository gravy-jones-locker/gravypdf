import itertools
import re
import numpy as np
import helper
from collections.abc import MutableSequence

class Nest(MutableSequence):

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
                    out.addtwig(elem, index=i)
                return out
            return inner

    def __init__(self, *elems, **kwargs):
        """
        Compile an iterable into a nest for the first time.
        """
        if kwargs.get('chain', False):
            elems = list(itertools.chain.from_iterable(elems))
        if kwargs.pop('copy', False):  
            self._ls = elems
            return  # Take types/idx from the copied nest
        
        self._ls = []
        for i, elem in enumerate(elems):
            
            if helper.chk_sys_it(elem):
                elem = type(self)(*elem, **kwargs)  
            elif not isinstance(elem, self.nested):
                elem = self.nested(elem)

            self.addtwig(elem, i)
        
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
            return type(self)(*self._ls[index], copy=True)
        return self._ls.__getitem__(index)

    def __iter__(self):
        for obj in self._ls:
            yield obj

    def addtwig(self, elem, index):
        """
        Append new element to sequence and assign index as default.
        """
        elem.i = index
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
    def cluster(self, fn, tol=5, store_parent=True):
        """
        Group nested elements by the attribute and function specified.
        """
        ref_ls = []  # Build list of points separated by tolerance
        
        for elem in self:
            if not any([x.clust(elem, fn, tol) for x in ref_ls]):
                ref_ls.append(elem)

        for ref in sorted(ref_ls, key=lambda x: fn(x)):
            cluster_ls = [x for x in self if x.clust(ref, fn, tol)]
            
            yield type(self)(*cluster_ls)

    @Decorators.rehome
    def denest(self, attr='__len__', flatten=False):
        """
        Expose all nested elements according to function specified.
        """
        for elem in self:
            
            if hasattr(elem, attr):
                sub_it = elem if attr == '__len__' else getattr(elem, attr)
                yield from type(self)(*sub_it).denest(attr)        
            
            if not hasattr(elem, attr) or not flatten:
                yield elem

    @Decorators.rehome
    def filter(self, fn=None, *args, **filters):
        """
        Return a filtered nest according to the keys/values in the mapping.
        """
        for elem in self:
            if not all([getattr(elem, k) == v for k, v in filters.items()]):
                continue
            if fn and not fn(elem, *args):
                continue
        
            yield elem

class Nested:

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

    def chk_intersection(self, y0=None, y1=None, x0=None, x1=None):
        """
        Return True if the element is inside the coordinates passed.
        """
        if x0 and self.x1 < x0 or x1 and self.x0 > x1:
            return False
        
        if y0 and self.y1 < y0 or y1 and self.y0 > y1:
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