.. datafork documentation master file, created by
   sphinx-quickstart on Sun Oct  6 15:24:38 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

datafork - transactional data for Python
========================================

`datafork` is a simple Python module that provides a transaction-like concept
to Python programs.

Programs create *slots* that each have an assigned value, and can then create
forked data states that change the values of slots without affecting the
parent state. The children can then be optionally merged back into their
parent as desired.

Contents:

.. toctree::
   :maxdepth: 2

   intro
   reference


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

