import os
import json

STATE_DIR = "/tmp/pyfunstate"


class CachedClass(object):
    def __init__(self, name):
        self.name = name
        sf = self._get_state_file("r")
        self._data_cache = json.loads(sf.read())
        sf.close()
        self._cache_context = None

    def clear(self):
        if self.get_cache_context() in self._data_cache:
            self._data_cache[self.get_cache_context()] = {}

    def clear_all(self):
        self._data_cache = {}

    def get_cache_context(self):
        return self._cache_context

    def get_contextless_cache(self):
        if True not in self._data_cache:
            self._data_cache[True] = {}
        return self._data_cache[True]

    def _get_state_file(self, mode):
        if not os.path.isdir(STATE_DIR):
            os.mkdir(STATE_DIR)
        fname = "funtoolstate_%s.json" % self.name
        fpath = os.path.join(STATE_DIR, fname)
        if not os.path.isfile(fpath):
            f = open(os.path.join(fpath), "w")
            f.write("{}")
            f.close()

        f = open(os.path.join(fpath), mode)
        return f

    def save_contextless_cache(self):
        sf = self._get_state_file("w")
        sf.write(json.dumps(self.get_contextless_cache()))
        sf.close()

    def clear_contextless_cache(self):
        sf = self._get_state_file("w")
        sf.write("{}")
        sf.close()
        self.get_contextless_cache().clear()

    def set_cache_context(self, context_value):
        self._cache_context = context_value


def cache(func, contextless=False):
    def wrapper(self, *args, **kwargs):
        if not isinstance(self, CachedClass):
            raise TypeError("Cache can only be called on subclasses of CachedClass!")
        func_name = func.__name__
        if func_name == "wrapper":
            raise Exception("Use cache decorator before any other decorator!")
        data = None
        kwargs_entries = sorted(list(kwargs.items()))
        cache_context = contextless or self.get_cache_context()
        if cache_context not in self._data_cache:
            self._data_cache[cache_context] = {}
        context_cache = self._data_cache[cache_context]
        if func_name not in context_cache:
            context_cache[func_name] = {}
        func_cache = context_cache[func_name]
        args_key = (str(args), str(kwargs_entries))
        if args_key not in func_cache:
            func_cache[args_key] = func(self, *args, **kwargs)
        data = func_cache[args_key]
        return data

        # if not
        #     cache_context = contextless or self.get_cache_context()
        #     self._data_cache[cache_context][func_name] = (
        #         (args, kwargs_entries),
        #         data,
        #     )
        # else:
        #     cache_args, data = self._data_cache.get(func_name)
        #     if cache_args != (self.get_cache_context(), args, kwargs_entries):
        #         data = func(self, *args, **kwargs)
        #         if not self.get_cache_context() in self._data_cache:
        #             self._data_cache[self.get_cache_context()] = {}
        #         self._data_cache[self.get_cache_context()][func_name] = (
        #             (args, kwargs_entries),
        #             data,
        #         )
        # return data

    return wrapper


def cache_contextless(func):
    return cache(func, contextless=True)

