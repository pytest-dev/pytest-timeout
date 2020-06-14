"""Setuptools install script for pytest-timeout."""
import io

from setuptools import setup

with io.open("README.rst", encoding="utf-8") as f:
    long_description = f.read()


setup(
    name="pytest-timeout",
    description="py.test plugin to abort hanging tests",
    long_description=long_description,
    version="1.4.0",
    author="Floris Bruynooghe",
    author_email="flub@devork.be",
    url="http://github.com/pytest-dev/pytest-timeout/",
    license="MIT",
    py_modules=["pytest_timeout"],
    entry_points={"pytest11": ["timeout = pytest_timeout"]},
    install_requires=["pytest>=3.6.0"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Plugins",
        "Intended Audience :: Developers",
        "License :: DFSG approved",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Testing",
    ],
)
