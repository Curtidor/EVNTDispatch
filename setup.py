from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="PyTrigger",
    version="0.0.0",
    description="PyTrigger: A Python event system enabling synchronous and asynchronous event handling within applications, ensuring efficient communication between different components.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        'pytest'
    ],
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
