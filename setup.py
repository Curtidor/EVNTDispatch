from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))

VERSION = '0.0.0'
DESCRIPTION = 'A Python event system'
# Setting up
setup(
    name="EVNTDispatch",
    version=VERSION,
    author="Curtidor",
    author_email="<tannermatos18@gmai.com>",
    description=DESCRIPTION,
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    packages=find_packages(),
    install_requires=['pytest'],
    keywords=['python'],
    classifiers=[
        "Development Status :: Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: Microsoft :: Windows",
    ]
)