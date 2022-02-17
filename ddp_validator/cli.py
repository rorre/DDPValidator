import argparse
import os
from pathlib import Path
import requests

from ddp_validator.constants import BASE_RESOURCES_URL, IS_FROZEN
from ddp_validator.online import fetch_update, load_classifiers
from ddp_validator.tester import InputTester
from ddp_validator.utils import console, get_classifier, get_program
from rich.panel import Panel
from rich.text import Text


def cli():
    if console.color_system == "windows":
        text = Text()
        text.append(
            "You are using Command Prompt/Powershell (conhost). ",
            style="bold",
        )
        text.append("Terminal output could be buggy.")
        text.append("\nIf you'd like to get the best out of this, ")
        text.append("please use the following terminals:")
        text.append("\n")
        text.append("\n\tAlacritty: https://alacritty.org/")
        text.append("\n\tHyper: https://hyper.is/")
        text.append("\n\tConEmu: https://conemu.github.io/")

        console.print(Panel(text, title="Notice"))

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

        console.rule("Test Start")
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

        console.rule("Test Start")
        console.print("Task:", test_classification["name"])
        tests = InputTester.from_file(
            str(program_path.resolve()),
            str(inputs_path.resolve()),
        )

    os.chdir(test_dir)
    tests.run_tests()
    console.rule("Test End")

    os.chdir(orig_cwd)
    input("Press enter to exit.")


if __name__ == "__main__":
    cli()
