from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = '0.0.0'
DESCRIPTION = 'A Python event system'
LONG_DESCRIPTION = 'EVENTDispatch is a event system that supports scheduling tasks, async events and sync events'

# Setting up
setup(
    name="EVNTDispatch",
    version=VERSION,
    author="Curtidor",
    author_email="<tannermatos18@gmai.com>",
    description=DESCRIPTION,
    packages=find_packages(),
    install_requires=['pytest'],
    keywords=['python'],
    classifiers=[
        "Development Status :: 1 - Development",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: Microsoft :: Windows",
    ]
)