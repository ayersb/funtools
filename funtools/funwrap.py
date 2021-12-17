import json
from functools import reduce
from collections.abc import Iterable

import pyperclip


class _FunWrap(Iterable):
    def pbcopy_json(self):
        self.pbcopy(as_json=True)

    def pbcopy(self, as_json=False):
        data = str(self)
        if as_json:
            data = json.dumps(self, indent=2)
        pyperclip.copy(data)

    def map(self, fn):
        if isinstance(self, dict):
            res = []
            for key, value in self.items():  # pylint: disable=no-member
                o = funwrap(fn(key, value))
                res.append(o)
            try:
                return FunDict(dict(res))
            except Exception:
                return FunList(res)
        elif isinstance(self, set):
            return FunSet(map(fn, self))
        else:
            return FunList(map(fn, self))

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

    # def unwrap(self):
    #     return


class FunDict(dict, _FunWrap):
    def __init__(self, d):
        super().__init__(d)

    def items(self):
        return FunList(super().items())

    def keys(self):
        return FunList(super().keys())

    def values(self):
        return FunList(super().values())

    def select(self, keys):
        d = FunDict({})
        for key in keys:
            alias = key
            if len(key) > 1:
                key = key[0]
                alias = key[1]
            d[alias] = self[key]
        return d

    def filter_keys(self, fn):
        kl = set(filter(fn, self.keys()))
        d = {}
        for k in self.keys():
            if k in kl:
                d[k] = self[k]
        return FunDict(d)

    def filter_values(self, fn):
        d = {}
        for k, v in self.items():
            if fn(v):
                d[k] = self[k]
        return FunDict(d)

    def sort_keys(self, **kwargs):
        sorted_keys = sorted(list(self.keys()), **kwargs)
        sd = {}
        for key in sorted_keys:
            sd[key] = self[key]
        return FunDict(sd)

    def invert(self):
        for v in self.values():
            if not isinstance(v, dict):
                raise ValueError("Can only invert keys of nested dicts!")
        nd = FunDict({})
        for okey, cdict in self.items():
            for nkey, v in cdict.items():
                if nkey not in nd:
                    nd[nkey] = {}
                if okey not in nd[nkey]:
                    nd[nkey][okey] = v
                else:
                    raise KeyError("Well that's confusing")

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


class FunList(list, _FunWrap):
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


def funwrap(collection):
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
