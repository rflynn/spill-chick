"""
$ python setup.py build
$ sudo python setup.py install
$ ./test.py

$ python3 -i


>>> from ngram3bin import ngram3bin
>>> ng = ngram3bin('ngram3.bin')
>>> ng.find(5,6,7)

"""

from distutils.core import setup, Extension

setup(name = 'ngram3bin',
      version = '1.0',
      ext_modules = [Extension('ngram3bin', ['ngram3bin.c','ngram3binpy.c'])])
