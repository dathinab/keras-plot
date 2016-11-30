"""
live ploting for keras by porting blocks-extras extension from
blocks-extras.extensions to keras
"""

from setuptools import setup, find_packages

# py2 combat
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# we use our README file as long description
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='keras-plot',

    # not 1.0 because it's still using the "old" bokeh interface
    version='0.1.0',
    description='enable live ploting through a port of blocks-extras.extensions.Plot to a keras callback',
    long_description=long_description,
    url='https://github.com/dathinab/keras-plot',
    author='Philipp Korber',
    author_email='philippkorber@gmail.com',
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',
        'Intended Audience :: Students',
        'Topic :: Scientific/Engineering :: Visualization',
        'License :: OSI Approved :: MIT License',

        # python 2 support might be dropped
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='keras live plot',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=['keras_plot'],

    # drop six if python 2 support is dropped
    install_requires=['keras', 'six', 'bokeh==0.10'],

    extras_require={
        'dev': [],
        'test': [],
    }
)
