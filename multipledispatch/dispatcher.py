from .conflict import ordering, ambiguities, super_signature, AmbiguityWarning
from warnings import warn

class Dispatcher(object):
    """ Dispatch methods based on type signature

    Use ``dispatch`` to add implementations

    Examples
    --------

    >>> from multipledispatch import dispatch
    >>> @dispatch(int)
    ... def f(x):
    ...     return x + 1

    >>> @dispatch(float)
    ... def f(x):
    ...     return x - 1

    >>> f(3)
    4
    >>> f(3.0)
    2.0
    """
    __slots__ = 'name', 'funcs', 'ordering', '_cache'

    def __init__(self, name):
        self.name = name
        self.funcs = dict()
        self._cache = dict()

    def register(self, *types):
        """ register dispatcher with new implementation

        >>> f = Dispatcher('f')
        >>> @f.register(int)
        ... def f(x):
        ...     return x + 1

        >>> @f.register(float)
        ... def f(x):
        ...     return x - 1

        >>> f(1)
        2

        >>> f(1.0)
        0.0
        """
        def _(func):
            self.add(types, func)
            return self
        return _

    def add(self, signature, func):
        """ Add new types/method pair to dispatcher

        >>> D = Dispatcher('add')
        >>> D.add((int, int), lambda x, y: x + y)
        >>> D.add((float, float), lambda x, y: x + y)

        >>> D(1, 2)
        3
        >>> D(1, 2.0)
        Traceback (most recent call last):
        ...
        NotImplementedError
        """
        self.funcs[signature] = func
        self.ordering = ordering(self.funcs)
        amb = ambiguities(self.funcs)
        if amb:
            warn(warning_text(self.name, amb), AmbiguityWarning)
        self._cache.clear()

    def __call__(self, *args, **kwargs):
        types = tuple([type(arg) for arg in args])
        func = self.resolve(types)
        return func(*args, **kwargs)

    def __str__(self):
        return "<dispatched %s>" % self.name
    __repr__ = __str__

    def resolve(self, types):
        """ Deterimine appropriate implementation for this type signature

        This method is internal.  Users should call this object as a function.
        Implementation resolution occurs within the ``__call__`` method.

        >>> from multipledispatch import dispatch
        >>> @dispatch(int)
        ... def inc(x):
        ...     return x + 1

        >>> implementation = inc.resolve((int,))
        >>> implementation(3)
        4

        >>> inc.resolve((float,))
        Traceback (most recent call last):
        ...
        NotImplementedError

        See Also:
            ``multipledispatch.conflict`` - module to determine resolution order
        """

        if types in self._cache:
            return self._cache[types]
        elif types in self.funcs:
            self._cache[types] = self.funcs[types]
            return self.funcs[types]

        n = len(types)
        for signature in self.ordering:
            if len(signature) == n and all(map(issubclass, types, signature)):
                result = self.funcs[signature]
                self._cache[types] = result
                return result
        raise NotImplementedError()


class MethodDispatcher(Dispatcher):
    """ Dispatch methods based on type signature

    See Also:
        Dispatcher
    """
    def __get__(self, instance, owner):
        self.obj = instance
        self.cls = owner
        return self

    def __call__(self, *args, **kwargs):
        types = tuple([type(arg) for arg in args])
        func = self.resolve(types)
        return func(self.obj, *args, **kwargs)


def str_signature(sig):
    """ String representation of type signature

    >>> str_signature((int, float))
    'int, float'
    """
    return ', '.join(cls.__name__ for cls in sig)


def warning_text(name, amb):
    """ The text for ambiguity warnings """
    text = "\nAmbiguities exist in dispatched function %s\n\n"%(name)
    text += "The following signatures may result in ambiguous behavior:\n"
    for pair in amb:
        text += "\t" + ', '.join('['+str_signature(s)+']' for s in pair) + "\n"
    text += "\n\nConsider making the following additions:\n\n"
    text += '\n\n'.join(['@dispatch(' + str_signature(super_signature(s))
                      + ')\ndef %s(...)'%name for s in amb])
    return text
