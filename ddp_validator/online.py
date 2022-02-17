import json
from typing import List, Tuple
import requests

from ddp_validator import __version__
from ddp_validator.constants import BASE_RESOURCES_URL, GITHUB_URL, IS_FROZEN
from ddp_validator.utils import console, parse_version
from ddp_validator.types import Classification


def load_classifiers() -> List[Classification]:
    classifiers: List[Classification]
    with console.status("Fetching classifiers..."):
        if IS_FROZEN:
            try:
                r = requests.get(BASE_RESOURCES_URL + "/classifier.json")
                if r.status_code != 200:
                    console.print(
                        "[white on red]ERROR:[/white on red]",
                        "GitHub returns non-200 status code.",
                    )
                    return []
                classifiers = r.json()
            except Exception:
                console.print(
                    "[white on red]ERROR:[/white on red]",
                    "Cannot fetch classifiers from GitHub!",
                )
                return []
        else:
            console.print(
                "[white on blue]NOTICE:[/white on blue]",
                "Using local classifiers",
            )
            with open("data/classifier.json", "r") as f:
                classifiers = json.load(f)

    return classifiers


def fetch_update():
    if not IS_FROZEN:
        console.print(
            "[white on blue]NOTICE:[/white on blue]", "Running in development mode."
        )
        return

    with console.status("Checking for updates..."):
        try:
            r = requests.get(GITHUB_URL)
            if r.status_code != 200:
                console.print(
                    "[on yellow]WARN:[/on yellow]",
                    "GitHub returns non-200 status code.",
                )
                return
            response = r.json()
        except Exception:
            console.print(
                "[on yellow]WARN:[/on yellow]",
                "An exception has occured during update fetching.",
            )
            return

    current_version = parse_version(__version__)
    new_version: Tuple[int, int, int] = parse_version(response["tag_name"])
    if current_version < new_version:
        console.print(
            "[white on blue]NOTICE:[/white on blue]",
            "New version available. Please download here:",
        )
        console.print("[white on blue]NOTICE:[/white on blue]", response["url"])
    else:
        console.print(
            "[white on blue]NOTICE:[/white on blue]",
            "You're running latest version.",
        )
