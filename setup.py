# -*- coding: utf-8 -*-
from setuptools import setup
import py2exe

packages = ["ddp_validator"]

package_data = {"": ["*"]}

install_requires = ["requests>=2.26.0,<3.0.0", "toml>=0.10.2,<0.11.0"]

setup_kwargs = {
    "name": "ddp-validator",
    "version": "0.2.0",
    "description": "",
    "long_description": None,
    "author": "Rendy Arya Kemal",
    "author_email": "renrror@gmail.com",
    "maintainer": None,
    "maintainer_email": None,
    "url": None,
    "packages": packages,
    "package_data": package_data,
    "install_requires": install_requires,
    "python_requires": ">=3.9,<3.11",
    "console": ["run.py"],
    "options": {
        "py2exe": {
            "optimize": 2,
            "excludes": ["tkinter", "_tkinter"],
            "compressed": True,
            "bundle_files": 1,
        }
    },
    "zipfile": None,
}


setup(**setup_kwargs)
