import re
from setuptools import setup, find_packages

# Read version from __init__.py
with open('__init__.py', 'r') as f:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    if version_match:
        version = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string in __init__.py")

setup(
    name="pyloupe",
    version=version,
    packages=find_packages(),
    install_requires=[
        "websockets>=10.0",
        "pyserial>=3.5",
        "Pillow>=9.0",
    ],
    extras_require={
        "dev": [
            "black==23.3.0",
            "flake8>=6.0.0",
            "pytest>=8.0",
            "mypy>=1.0.0",
            "sphinx>=7.0.0",
            "build>=1.0.0",
            "twine>=4.0.0",
            "pytest-cov>=4.1.0",
        ],
    },
    python_requires=">=3.7",
    author="Loupedeck Contributors",
    author_email="",  # Add author email if available
    description="A Python library for controlling Loupedeck devices",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/foxxyz/pyloupe",  # Update with correct URL
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Hardware :: Hardware Drivers",
    ],
    keywords="loupedeck, stream controller, hardware, api",
)
