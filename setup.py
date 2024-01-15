from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))

VERSION = '0.0.1'
DESCRIPTION = (
    "EVNTDispatch is a Python event system for seamless event-driven "
    "programming, offering flexibility and efficiency in handling and dispatching events."
)

# Setting up
setup(
    name="EVNTDispatch",
    version=VERSION,
    author="Curtidor",
    author_email="tannermatos18@gmai.com",
    description=DESCRIPTION,
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    packages=find_packages(),
    install_requires=['pytest'],
    keywords=['EVNTDispatch', 'event system', 'event dispatcher', 'event-driven programming',
              'synchronous events', 'asynchronous events', 'publish-subscribe',
              'developer tools', 'Python 3', 'cross-platform'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: Microsoft :: Windows",
    ]
)