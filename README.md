# Funtools
Python tools for use in interactive shells


## FunWrap

This package provides several classes that wrap around basic collect types and allow manipulation of the collections using a functional programming style operations. _The operations are not optimized from a performance standpoint and shouldn't be used in production code_, but can be very helpful for doing quick manipulations of data in an environment like an `ipython` shell.

Some brief examples

```python
l = fn([2,4,6,2,3,3,3]) # fn will return a FunList collection
l.filter(lambda x : x % 2 ==0 ).map(lambda x: x **2) # returns [4, 16, 36, 4]
l.freq().ksort() # returns {2: 2, 4: 1, 6: 1, 3: 3}
```

### Examples
[funwrap examples](./examples/FunWrapExamples.md)

## FunCache

This package provides a class and decorators that can be used to create versions of other classes that cache the results of operations in memory. This is particularly useful when wrapping API clients. Using the funwraped types on cached API clients lets you quickly manipulate data fetched from APIs and stitch many API calls together in a way that's repeatable later but doesn't require data to be refetched every time you add a new operation.

A hypothetical example:

```python
c = MyCachedCloudComputeApiClient(profile='/foo/bar/config')
slist = c.list_regions() # Get a list of all regions from your cloud platform API
 .map(lambda r: c.list_compute(region=r.id)) # Fetches all VMs for each region, this could take a while
 .flatten() # Flatten the resulting lists
 .filter(lambda vm: vm.type == "bigexpensivetype") # If we have the list_compute calls cached, this will return quickly
 .map(lambda vm: vm.metadata.created_by) # Say this returns a User id
 .freq() # This will return a FunDict with counts of expensive instances by user id {'xya134adf3': 51,...}
 .map(lambda uid, count: (c.get_user(uid).email, count)) # Maps over dict grabbing user records, only expensive 1st time if cached
 .vfilter(lambda count: count > 2) # {'brandontheresourcehog@urcompany.com': 51, ...}
```

Using the `ipython` terminal these commands will be saved in the terminal history and can quickly be searched for an expanded upon later, or dumped into a script.

