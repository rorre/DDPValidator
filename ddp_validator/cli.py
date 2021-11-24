import argparse
import os
from pathlib import Path
from typing import List
from ddp_validator.tester import InputTester
from ddp_validator.types import Classification
from ddp_validator.utils import get_classifier, get_program
import json

with open("data/classifier.json", "r") as f:
    classifiers: List[Classification] = json.load(f)


def cli():
    parser = argparse.ArgumentParser(description="Lab Tester.")
    parser.add_argument("code", help="Lab codename")

    args = parser.parse_args()

    orig_cwd = os.getcwd()

    test_dir = Path(args.code)
    program_path = get_program(test_dir).absolute()

    test_classification = get_classifier(program_path, classifiers)
    if not test_classification:
        raise Exception("Cannot decide which task.")

    print("Task:", test_classification["name"])
    inputs_path = Path("data") / test_classification["path"]

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
