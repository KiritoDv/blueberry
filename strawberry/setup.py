from distutils.core import setup, Extension

module1 = Extension('strawberry', sources = ['straw.c'])

setup (name = 'strawberry',
       version = '1.0',
       description = 'Strawberry miniaudio wrapper',
       ext_modules = [module1])