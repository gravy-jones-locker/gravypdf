def lazy_property(func):
    """
    Lazy property evaluated on first call of decorated method.
    """
    @property
    def inner(cls):
        if not hasattr(cls, f'_{func.__name__}'):
            func(cls)
        return getattr(cls, f'_{func.__name__}')
    return inner

def filter_consecutive(ls):
    """
    Return True values where one other True to side.
    """
    testProx = lambda x, i: (i < len(ls) - 1 and ls[i+1]) or ls[i-1]
    
    return [x for i, x in enumerate(ls) if x and testProx(x, i)]

def store_attrs(tar, ref, non_sys=True):
    """
    Attach the attributes from the mapping/ref object to the target object.
    """
    if not isinstance(ref, dict):
        ref = {k:getattr(ref, k) for k in dir(ref)}
    
    for attr, val in ref.items():
        if (non_sys and attr.startswith('__')) or not val:
            continue
        try:
            setattr(tar, attr, val)
        except:
            pass  # True for method properties

def chk_sys_it(it):
    """
    Returns True if the input is a builtin iterable.
    """
    return hasattr(it, '__len__') and type(it).__module__ == 'builtins'