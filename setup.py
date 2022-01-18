"""Setuptools install script for pytest-timeout."""
from setuptools import setup

with open("README.rst", encoding="utf-8") as f:
    long_description = f.read()


setup(
    name="pytest-timeout",
    description="pytest plugin to abort hanging tests",
    long_description=long_description,
    version="2.1.0",
    author="Floris Bruynooghe",
    author_email="flub@devork.be",
    url="https://github.com/pytest-dev/pytest-timeout",
    license="MIT",
    py_modules=["pytest_timeout"],
    entry_points={"pytest11": ["timeout = pytest_timeout"]},
    install_requires=["pytest>=5.0.0"],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Plugins",
        "Intended Audience :: Developers",
        "License :: DFSG approved",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Testing",
        "Framework :: Pytest",
    ],
)
