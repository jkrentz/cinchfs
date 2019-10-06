#!/usr/bin/env python3
 
def first(iterable, default=None, key=None):
    if key is None:
        for el in iterable:
            if el is not None:
                return el
    else:
        for el in iterable:
            if key(el) is not None:
                return el
    return default
