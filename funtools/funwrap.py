from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from functools import reduce
from inspect import signature
from typing import Any, Dict, List, Set, Tuple, Type, TypeVar, Union

import pyperclip

T = TypeVar("T")
O = TypeVar("O")

V = TypeVar("V")
K = TypeVar("K")


class RegexQuick:
    regex_cache = {}  # Cuz not :P

    @classmethod
    def __call__(clz, pattern):
        regex = None
        if pattern in clz.regex_cache:
            regex = clz.regex_cache[pattern]
        else:
            regex = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
            clz.regex_cache[pattern] = regex
        return regex.match


rx = RegexQuick()


def _fun_map(fn, itterables):
    return [fn(x) for x in itterables]


def _fun_dict_map(fn, dictionary):
    res = []
    for key, value in dictionary.items():  # pylint: disable=no-member
        o = funwrap(fn(key, value))
        res.append(o)
    return res


class _FunWrap(Iterable):
    def pbcopy_json(self):
        self.pbcopy(as_json=True)

    def pbcopy(self, as_json=False):
        data = str(self)
        if as_json:
            data = json.dumps(self, indent=2)
        pyperclip.copy(data)

    def map(self, fn: Callable[[T], O]) -> Iterable:
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

    def freq(self, fn=None) -> FunDict[T, int]:
        freq_map = {}
        l = self
        if isinstance(self, dict):
            l = self.values()
        for v in l:
            try:
                hash(v)
            except TypeError:
                v = str(v)
            # If there's a match function, use it
            if fn is not None and not fn(v):
                continue
            if v not in freq_map:
                freq_map[v] = 0
            freq_map[v] += 1
        return FunDict(freq_map)


class FunDict(Dict[K, V], _FunWrap):
    def __init__(self, d: Dict[K, V]):
        super().__init__(d)

    def __getitem__(self, val):
        res = super().__getitem__(val)
        if isinstance(res, list):
            return FunList(res)
        if isinstance(res, dict):
            return FunDict(res)
        return res

    def items(self) -> FunList[Tuple[K, V]]:
        return FunList(super().items())

    def keys(self) -> FunList[K]:
        return FunList(super().keys())

    def values(self) -> FunList[V]:
        return FunList(super().values())

    def select(self, *keys: K | (K, str)) -> FunDict[K, V]:
        d = FunDict({})
        for key in keys:
            alias = key
            # If an entry in keys is tuple-like, rename the selected key
            if isinstance(key, (list, tuple)) and len(key) > 1:
                key = key[0]
                alias = key[1]
            d[alias] = self[key]
        return d

    def kmap(self, fn: Callable[[K], O]) -> FunList[O]:
        return FunList(map(fn, self.keys()))

    def vmap(self, fn: Callable[[V], O]) -> FunList[O]:
        return FunList(map(fn, self.values()))

    def kfilter(self, fn: Callable[[K], bool]) -> FunDict[K, V]:
        kl = set(filter(fn, self.keys()))
        d = {}
        for k in self.keys():
            if k in kl:
                d[k] = self[k]
        return FunDict(d)

    def vfilter(self, fn: Callable[[V], bool]) -> FunDict[K, V]:
        d = {}
        for k, v in self.items():
            if fn(v):
                d[k] = self[k]
        return FunDict(d)

    def ksort(self, fn=lambda x: x) -> FunDict[K, V]:
        sorted_items = sorted(self.items(), key=lambda t: fn(t[0]))
        return FunDict(sorted_items)

    def vsort(self, fn=lambda x: x) -> FunDict[K, V]:
        sorted_items = sorted(self.items(), key=lambda t: fn(t[1]))
        return FunDict(sorted_items)

    def invert(self, smart_flatten=True) -> FunDict[K, Sequence[V]]:
        if not len(self):
            return {}
        entry_types = {"dict": 0, "str": 0, "int": 0, "float": 0}
        for v in self.values():
            if isinstance(v, dict):
                entry_types["dict"] += 1
            elif isinstance(v, str):
                entry_types["str"] += 1
            elif isinstance(v, int):
                entry_types["int"] += 1
            elif isinstance(v, float):
                entry_types["float"] += 1
            else:
                raise RuntimeError(
                    "Only dicts with keys of types '%s' can be inverted, but type %s found"
                    % (str(entry_types), type(v))
                )

        types_present = list(filter(lambda t: t[1], entry_types.items()))
        if len(types_present) > 1:
            # TODO: make print more pretty
            raise RuntimeError(
                "Only dicts with keys of *one* matching type can be inverted, but %s found"
                % str(entry_types)
            )
        key_type = types_present.pop()[0]
        nd = FunDict({})
        for k0, v0 in self.items():
            if key_type == "dict":
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

    @property
    def len_keys(self):
        return len(self)

    @property
    def leng_values(self):
        ll = 0
        for value in self.values():
            if isinstance(value, list):
                ll += len(value)
            elif isinstance(value, dict):
                ll += FunDict(value).len_values()
            else:
                ll += 1
        return ll


class FunList(List[T], _FunWrap):
    def __init__(self, l=None):
        if not l:
            l = []
        super().__init__(l)

    def __getitem__(self, val):
        res = super().__getitem__(val)
        if isinstance(res, list):
            return FunList(res)
        if isinstance(res, dict):
            return FunDict(res)
        return res

    def sum(self):
        return sum(self)

    def sort(self, fn=None, **kwargs) -> FunList[T]:
        if fn is not None:
            if "key" in kwargs:
                raise RuntimeError(
                    "Cannot pass both a 'key' kwarg and a argument to sort!"
                )
            kwargs["key"] = fn
        return FunList(sorted(self, **kwargs))

    @property
    def len(self) -> int:
        return len(self)

    @property
    def length(self) -> int:
        return len(self)

    @property
    def head(self):
        return self[0] if len(self) else None

    @property
    def tail(self) -> T:
        return self[-1] if len(self) else None

    def filter(self, fn: Callable[[T], bool]) -> FunList[T]:
        return FunList(list(filter(fn, self)))

    def flatten(self) -> FunList[Any]:
        nl = []
        for e in self:
            if isinstance(e, list):
                nl += e
            else:
                nl.append(e)

        return FunList(nl)

    def flatten_dicts(self) -> FunDict[Any]:
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


def funwrap(collection: Iterable):
    def match(x, types):
        return bool(list(filter(lambda t: isinstance(x, t), types)))

    dict_types = [dict, type({}.items())]
    list_types = [list, Iterable]

    if isinstance(collection, str):
        return collection
    if match(collection, dict_types):
        return FunDict(collection)
    if match(collection, list_types):
        return FunList(collection)
    return collection


class TestClass:
    def dothing(self, x) -> FunFunDict[K, V]:
        return FunDict(x)


# Decorator
def fun(func):
    def wrapper(*args, **kwargs):
        return funwrap(func(*args, **kwargs))

    wrapper.__doc__ = func.__doc__
    return wrapper
