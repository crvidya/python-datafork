datafork
========

``datafork`` is a Python utility library for creating data slots whose content
can be temporarily "forked", possibly mutated, and then merged back into what
was already present.

This allows for code to evaluate "what if" scenarios, and then conditionally
merge the result depending on whether the outcome was acceptable.

This model could be thought of as a sort of "transactional memory", though
it also evokes the idea of dynamic scope.

The simplest use-case is a transaction block whose side-effects apply only
if the block runs to completion without raising an exception::

    import datafork

    with datafork.root() as root:
        example_slot = root.slot(initial_value=1)
        with root.transaction():
            example_slot.value = 2
            might_raise_exception()
        # this will print 1 if an exception was raised, or 2 if not.
        print example_slot.value

For other examples and reference documentation, see the manual.

Installation
------------

Stable versions of this module can be installed from pypi as ``datafork``.

Development Environment Setup
-----------------------------

If you'd like to contribute to this library you can clone this repository
and run the following steps to get set up. This assumes you already have
Python installed, and virtualenv available.

 * ``virtualenv env``
 * ``source env/bin/activate``
 * ``pip install -r requirements-dev.txt``

You should then be able to run the tests by running ``nosetests``.

Contributing
------------

Contributions are welcome but please ensure that any changes are tested and
that code style follows what's already present. The baseline code style for
this library is PEP8.
