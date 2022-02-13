import argparse
import os
from pathlib import Path
from typing import List, Tuple
from ddp_validator import __version__
from ddp_validator.tester import InputTester
from ddp_validator.types import Classification
from ddp_validator.utils import get_classifier, get_program, parse_version, console
import json
import requests
import sys

BASE_RESOURCES_URL = "https://raw.githubusercontent.com/rorre/DDPValidator/main/data"
GITHUB_URL = "https://api.github.com/repos/rorre/DDPValidator/releases/latest"
IS_FROZEN = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


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


def cli():
    fetch_update()
    parser = argparse.ArgumentParser(description="Lab Tester.")
    parser.add_argument("code", help="Lab codename")
    parser.add_argument("--debug", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    console.set_debug(args.debug)
    orig_cwd = os.getcwd()
    test_dir = Path(args.code)
    program_path = get_program(test_dir).absolute()

    classifiers = load_classifiers()
    test_classification = get_classifier(program_path, classifiers)
    if not test_classification:
        raise Exception("Cannot decide which task.")

    inputs_path = Path("data") / test_classification["path"]

    if IS_FROZEN:
        try:
            console.print(
                "[white on blue]NOTICE:[/white on blue]", "Fetching test data..."
            )
            r = requests.get(BASE_RESOURCES_URL + "/" + test_classification["path"])
            if r.status_code != 200:
                console.print(
                    "[white on red]ERROR:[/white on red]",
                    "GitHub returns non-200 status code.",
                )
                return
        except Exception:
            console.print(
                "[white on red]ERROR:[/white on red]",
                "Cannot fetch test data from GitHub!",
            )
            return

        console.line()
        console.print("Task:", test_classification["name"])
        tests = InputTester.from_str(
            str(program_path.resolve()),
            r.text,
        )
    else:
        console.print(
            "[white on blue]NOTICE:[/white on blue]",
            "Develepment mode, using local test data.",
        )

        console.line()
        console.print("Task:", test_classification["name"])
        tests = InputTester.from_file(
            str(program_path.resolve()),
            str(inputs_path.resolve()),
        )

    os.chdir(test_dir)
    tests.run_tests()
    os.chdir(orig_cwd)
    input("Press enter to exit.")


if __name__ == "__main__":
    cli()
