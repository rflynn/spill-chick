"""
How To Use

$ python setup.py build
$ sudo python setup.py install
$ time python3 -i < testbin.py

"""

from distutils.core import setup, Extension

setup(name = 'ngram3bin',
      version = '1.0',
      ext_modules = [Extension('ngram3bin', ['ngram3bin.c','ngram3binpy.c'])])
