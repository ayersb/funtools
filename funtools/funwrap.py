import json
from functools import reduce
from collections.abc import Mapping, Sequence, Iterable, Callable
from typing import TypeVar, Tuple, Set, List, Dict, Union
from inspect import signature

import pyperclip

T = TypeVar("T")
O = TypeVar("O")

V = TypeVar("V")
K = TypeVar("K")


def _fun_map(fn, *itterables):
    l = []
    sig = signature(fn)
    for lentry in itterables:
        for i, x in enumerate(lentry):
            if len(signature(fn).parameters) > 1:  # TODO: Ignore kwargs
                l.append(fn(x, i))
            else:
                l.append(fn(x))
    return l


def _fun_dict_map(fn, dictionary):
    res = []
    for key, value in dictionary.items():  # pylint: disable=no-member
        o = funwrap(fn(key, value))
        res.append(o)
    return res


class _FunWrap(Iterable[T]):
    def pbcopy_json(self):
        self.pbcopy(as_json=True)

    def pbcopy(self, as_json=False):
        data = str(self)
        if as_json:
            data = json.dumps(self, indent=2)
        pyperclip.copy(data)

    def map(self, fn: Callable[[T], O]) -> Iterable[O]:
        """Returns a new FunCollection after applying fn to each element of the collection"""
        if isinstance(self, dict):
            res = _fun_dict_map(fn, self)
            try:
                return FunDict(dict(res))
            except Exception:
                return FunList(res)
        elif isinstance(self, set):
            return FunSet(_fun_map(fn, self))
        else:
            # TODO: Handle indexs
            return FunList(_fun_map(fn, self))

    def reduce(self, fn, initial=None):
        def dict_wrap_fn(col, kvp):
            return fn(col, kvp[0], kvp[1])

        itter = self
        rfn = fn
        if isinstance(self, dict):
            itter = list(self.items())  # pylint: disable=no-member
            rfn = dict_wrap_fn

        output = None
        if initial is not None:
            output = reduce(rfn, itter, initial)
        else:
            output = reduce(rfn, itter)

        return funwrap(output)

    def sort(self, key=None, **kwargs):
        sort_key_fn = None
        if key:
            sort_key_fn = lambda a: key(a[0], a[1])  # noqa
        if isinstance(self, dict):
            items = list(self.items())  # pylint: disable=no-member
            items.sort(key=sort_key_fn, **kwargs)
            return FunDict(dict(items))
        else:
            items = self
            items.sort(**kwargs)
            return FunList(items)

    def sum(self):
        return sum(self)


class FunDict(Dict[K, V], _FunWrap):
    def __init__(self, d: Dict[K, V]):
        super().__init__(d)

    def items(self) -> List[Tuple[K, V]]:
        return FunList(super().items())

    def keys(self) -> List[K]:
        return FunList(super().keys())

    def values(self) -> List[V]:
        return FunList(super().values())

    def select(self, keys: Sequence[K]) -> Dict[K, V]:
        d = FunDict({})
        for key in keys:
            alias = key
            if len(key) > 1:
                key = key[0]
                alias = key[1]
            d[alias] = self[key]
        return d

    def kfilter(self, fn: Callable[[K], bool]) -> Dict[K, V]:
        kl = set(filter(fn, self.keys()))
        d = {}
        for k in self.keys():
            if k in kl:
                d[k] = self[k]
        return FunDict(d)

    def vfilter(self, fn: Callable[[V], bool]) -> Dict[K, V]:
        d = {}
        for k, v in self.items():
            if fn(v):
                d[k] = self[k]
        return FunDict(d)

    def ksort(self, fn) -> Dict[K, V]:
        sorted_items = sorted(self.items(), key=lambda t: fn(t[0]))
        return FunDict(sorted_items)

    def vsort(self, fn) -> Dict[K, V]:
        sorted_items = sorted(self.items(), key=lambda t: fn(t[1]))
        return FunDict(sorted_items)

    def invert(self, smart_flatten=True) -> Dict[K, Sequence[V]]:
        if not len(self):
            return {}
        entry_types = {
            'dict': 0,
            'str': 0,
            'int': 0,
            'float': 0
        }
        for v in self.values():
            if isinstance(v, dict):
                entry_types['dict'] += 1
            elif isinstance(v, str):
                entry_types['str'] += 1
            elif isinstance(v, int):
                entry_types['int'] += 1
            elif isinstance(v, float):
                entry_types['float'] += 1
            else:
                raise RuntimeError("Only dicts with keys of types '%s' can be inverted, but type %s found" % (str(entry_types), type(v)))

        types_present = list(filter(lambda t: t[1], entry_types.items()))
        if len(types_present) > 1:
            # TODO: make print more pretty
            raise RuntimeError("Only dicts with keys of *one* matching type can be inverted, but %s found" % str(entry_types))
        key_type = types_present.pop()[0]
        nd = FunDict({})
        for k0, v0 in self.items():
            if key_type == 'dict':
                for nkey, v in cdict.items():
                    if nkey not in nd:
                        nd[nkey] = {}
                    if okey not in nd[nkey]:
                        nd[nkey][okey] = v
                    else:
                        raise KeyError("Well that's confusing")
            else:
                if v0 not in nd:
                    nd[v0] = []
                nd[v0].append(k0)

        if smart_flatten:
            # If all values lists are of lenth one, unwrap them before returning
            # Makes it less annoying to work with data where k -> v mapping is 1:1
            lset = set(map(len, nd.values()))
            if len(lset) == 1 and 1 in lset:
                for k, v in list(nd.items()):
                    nd[k] = v[0]
        return nd

    def length_keys(self):
        return len(self)

    def length_values(self):
        ll = 0
        for value in self.values():
            if isinstance(value, list):
                ll += len(value)
            elif isinstance(value, dict):
                ll += FunDict(value).length_values()
            else:
                ll += 1
        return ll


class FunList(List[T], _FunWrap):
    def __init__(self, l=None):
        if not l:
            l = []
        super().__init__(l)

    def __getitem__(self, val):
        sliced = super().__getitem__(val)
        if not isinstance(sliced, list):
            return sliced

        return FunList(sliced)

    def sort(self, **kwargs):
        return FunList(sorted(self, **kwargs))

    def length(self):
        return len(self)

    def filter(self, fn):
        return FunList(list(filter(fn, self)))

    def head(self):
        return self[0] if len(self) else None

    def tail(self):
        return self[-1] if len(self) else None

    def flatten(self):
        nl = []
        for e in self:
            if isinstance(e, list):
                nl += e
            else:
                nl.append(e)

        return FunList(nl)

    def flatten_dicts(self):
        for e in self:
            if not isinstance(e, dict):
                raise ValueError("All entries must be dicts")
            d = {}
            for e in self:
                for k, v in e.items():
                    if k not in d:
                        d[k] = FunList()
                    if isinstance(v, list):
                        d[k] += v
                    else:
                        d[k].append(v)
            return FunDict(d)

    def to_dict(self, key_fn=None, group_values=False):
        d = {}
        for entry in self:
            k = None
            v = None
            if key_fn:
                k = key_fn(entry)
                v = entry
            else:
                if len(entry) != 2:
                    raise ValueError("Cannot convert to dict, not composed to kv pairs")
                k = entry[0]
                v = entry[1]

            if group_values:
                if not k in d:
                    d[k] = FunList()
                d[k].append(v)
            else:
                d[k] = v
        return FunDict(d)

    def group_by(self, key_fn):
        return self.to_dict(key_fn=key_fn, group_values=True)

    def to_set(self):
        return FunSet(self)


class FunSet(set, _FunWrap):
    def __init__(self, s=set()):
        super().__init__(s)

    def to_list(self):
        return FunList(self)


def funwrap(collection: Iterable[T]):
    def match(x, types):
        return bool(list(filter(lambda t: isinstance(x, t), types)))

    dict_types = [dict, type({}.items())]
    list_types = [list, Iterable]

    if match(collection, dict_types):
        return FunDict(collection)
    if match(collection, list_types):
        return FunList(collection)
    return collection


# Decorator
def fun(func):
    def wrapper(*args, **kwargs):
        return funwrap(func(*args, **kwargs))

    wrapper.__doc__ = func.__doc__
    return wrapper
