import asyncio

from asyncio.subprocess import PIPE
from pathlib import Path
from typing import Any, Callable, Generic, List, Optional, Tuple, TypeVar

from rich.console import Console
from rich.prompt import Prompt

from ddp_validator.types import Classification

F = TypeVar("F", bound=Callable[..., Any])


class copy_signature(Generic[F]):
    def __init__(self, target: F) -> None:
        ...

    def __call__(self, wrapped: Callable[..., Any]) -> F:
        return wrapped  # type: ignore


class DebuggableConsole(Console):
    @copy_signature(Console.__init__)
    def __init__(self, *args, **kwargs):
        self._debug = False
        super().__init__(*args, **kwargs)

    def set_debug(self, value: bool):
        self._debug = value

    @copy_signature(Console.log)
    def debug(self, *args, **kwargs):
        if self._debug:
            return self.log(*args, **kwargs)


console = DebuggableConsole()


async def run_command(test_stdin: List[str], *args):
    console.debug("Running command:", " ".join(args))
    console.debug("stdin:", test_stdin)

    process = await asyncio.create_subprocess_exec(
        *args, stdout=PIPE, stderr=PIPE, stdin=PIPE
    )
    assert process.stdin
    assert process.stdout
    assert process.stderr

    combined_io = ""
    i = 0
    for submitting_line in test_stdin:
        while True:
            try:
                c = await asyncio.wait_for(process.stdout.read(1), 0.1)
                combined_io += c.decode()
            except asyncio.TimeoutError:
                break

        console.debug("Writing line:", submitting_line)
        process.stdin.write(submitting_line.encode() + b"\r\n")
        await process.stdin.drain()

        combined_io += submitting_line + "\n"
        i += 1

    stderr = (await process.stderr.read()).decode()
    if stderr:
        raise Exception("Program errored!\r\n\r\n" + stderr)

    console.debug("Program finishes, exiting")
    combined_io += (await process.stdout.read()).decode()
    process.kill()
    return [
        s.encode("unicode_escape").decode("utf-8")
        for s in combined_io.strip().splitlines()
    ]


def get_program(dir: Path):
    valid_programs: List[Path] = []
    for p in dir.iterdir():
        if p.suffix == ".py":
            valid_programs.append(p)

    if len(valid_programs) > 1:
        console.print("Multiple Python file found, pick one that you want to test:")
        for i, p in enumerate(valid_programs):
            console.print(f"[{i + 1}] {p.name}")

        while True:
            idx = int(Prompt.ask("Pick one: ", console=console)) - 1
            if 0 <= idx < len(valid_programs):
                break

        return valid_programs[idx]
    return valid_programs[0]


def get_classifier(
    program_path: Path, classifiers: List[Classification]
) -> Optional[Classification]:
    with open(program_path, "r") as f:
        program_content = f.read()

    for c in classifiers:
        if c["identifier"] in program_content:
            return c
    return None


def parse_version(ver: str) -> Tuple[int, ...]:
    return tuple(map(int, ver.split(".")))
