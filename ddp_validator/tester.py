import asyncio
import difflib
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, cast

import toml
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from asyncio.subprocess import PIPE
from ddp_validator.types import Test, TestDict
from ddp_validator.utils import console, run_command

if console.color_system == "windows":
    failed = "[red]FAILED[/red]"
    success = "[green]SUCCESS[/green]"
else:
    failed = "❌"
    success = "✔️"


def has_subset(first, second):
    for line in first:
        for second_line in second:
            if line == second_line:
                return True
    return False


def compare_output(
    program_lines: List[str],
    expected_lines: List[str],
    subset: bool = False,
):
    if subset:
        subset_exist = has_subset(program_lines, expected_lines)
        subset_exist |= has_subset(expected_lines, program_lines)
        return subset_exist

    if len(program_lines) != len(expected_lines):
        return False

    for i in range(len(program_lines)):
        current_expected = expected_lines[i]

        # Regex
        if current_expected.startswith("regex|"):
            current_expected = current_expected[6:]
            result = re.match(current_expected, program_lines[i])
            if not result:
                return False
            continue

        if program_lines[i] != expected_lines[i]:
            return False

    return True


def check_output_file(expected_path: Path, output_path: Path):
    with open(expected_path) as f_expected, open(output_path) as f_output:
        expected = [
            s.encode("unicode_escape").decode("utf-8") for s in f_expected.readlines()
        ]
        output = [
            s.encode("unicode_escape").decode("utf-8") for s in f_output.readlines()
        ]

        console.debug("Expected:", expected)
        console.debug("Output:", output)

        return expected == output


class InputTester:
    def __init__(
        self,
        program_path: str,
        tests: List[Test],
        language: str,
        compile_command: str,
        workdir: Optional[str] = None,
    ):
        self._tests = tests
        self._program = program_path
        self._workdir = workdir
        self._language = language
        self._compile_command = compile_command

        if sys.platform == "win32":
            console.debug("Windows, using ProactorEventLoop.")

            # Windows subprocess pipes fix
            self._loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(self._loop)
        else:
            self._loop = asyncio.get_event_loop()

    def run_compile(self):
        if not self._compile_command:
            return

        console.print("Compiling program...")
        cmd = self._compile_command.format_map({"program": self._program})
        console.debug("Compiling with command", cmd)

        async def run_cmd():
            process = await asyncio.create_subprocess_exec(
                cmd.split(" ")[0],
                *cmd.split(" ")[1:],
                stdout=PIPE,
                stderr=PIPE,
                stdin=PIPE,
            )
            await process.wait()

            assert process.returncode is not None
            assert process.stdout
            assert process.stderr

            return (
                process.returncode,
                await process.stdout.read(),
                await process.stderr.read(),
            )

        code, stdout, stderr = self._loop.run_until_complete(run_cmd())
        if code != 0:
            raise Exception("Error occured!\r\n\r\n" + stderr.decode())

        stdout_data = stdout.decode()
        console.print("Compiled.", end="")
        if stdout_data:
            console.print("stdout:")
            console.print(stdout_data)
        else:
            console.print()

    def run_tests(self):
        self.run_compile()

        if self._language == "python":
            cmd = ("python", self._program)
        else:
            cmd = ("java", Path(self._program).name)

        test_passed = True
        progress = Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=console,
            expand=True,
            transient=True,
        )
        task = progress.add_task("[green]Running tests...", total=len(self._tests))

        with progress:
            for t in self._tests:
                console.debug("Running test", t["title"])
                program_lines = self._loop.run_until_complete(
                    run_command(t["stdin"].splitlines(), *cmd)
                )
                expected_lines = [
                    s.encode("unicode_escape").decode("utf-8")
                    for s in t["stdout"].splitlines()
                ]

                console.debug("Program lines:", program_lines)
                console.debug("Expected lines", expected_lines)

                condition = compare_output(program_lines, expected_lines, t["subset"])
                if not condition:
                    console.debug("Output differs from expected.")
                    console.print(f"{t['title']:<20} : {failed}")

                    if not (t["has_regex"] or t["subset"]):
                        target_html = f"difference-{t['title']}.html"
                        console.debug("Writing HTML difference to", target_html)

                        differ = difflib.HtmlDiff()
                        html = differ.make_file(
                            expected_lines,
                            program_lines,
                            fromdesc="Expected",
                            todesc="Program Output",
                        )
                        with open(target_html, "w") as f:
                            f.write(html)

                    test_passed = False
                    progress.advance(task)
                    continue

                if t["expected_file"] and t["output_file"]:
                    console.debug("Output file is required for check")

                    if not check_output_file(t["expected_file"], t["output_file"]):
                        console.debug("Output file does not match output.")
                        console.print(f"{t['title']:<20} : {failed} (Output file)")
                        test_passed = False
                        progress.advance(task)
                        continue

                console.debug("Check passed.")
                console.print(f"{t['title']:<20} : {success}")
                progress.advance(task)

        if test_passed:
            console.print("All checks passed!")
        else:
            console.print("Some checks have failed :(")

    @classmethod
    def from_str(cls, program_path: str, inputs: str):
        tests: List[Test] = []
        tests_dict: Dict[str, TestDict] = toml.loads(inputs)  # type: ignore

        language = cast(str, tests_dict.pop("language"))
        compile_command = cast(str, tests_dict.pop("compile", ""))

        console.debug("Loading test config")
        console.debug(tests_dict)

        for k in tests_dict:
            console.debug("Got new test", k)

            t = tests_dict[k]
            test_data: Test = {
                "title": k,
                "stdin": t["input"].strip(),
                "stdout": t["output"].strip(),
                "subset": t["subset"],
                "expected_file": t["expected_file"] if "expected_file" in t else None,
                "output_file": t["output_file"] if "output_file" in t else None,
                "has_regex": "regex|" in t["output"],
            }

            console.debug(test_data)
            tests.append(test_data)

        return cls(program_path, tests, language, compile_command)

    @classmethod
    def from_file(cls, program_path: str, fname: str):
        console.debug("Reading", fname)
        with open(fname, "r") as f:
            inputs = f.read()

        return cls.from_str(program_path, inputs)
