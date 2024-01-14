from setuptools import setup, find_packages

setup(
    name='PYTrigger',
    version='0.0.0',
    packages=find_packages(),
    license='MIT',
    install_requires=[
        'pytest'
    ],
    description="A Python event system enabling synchronous and asynchronous event handling within applications, ensuring efficient communication between different components.",
    long_description=open('README.txt').read(),
)
