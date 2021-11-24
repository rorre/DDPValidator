from typing import Optional, TypedDict


class _TestDictBase(TypedDict):
    input: str
    output: str
    subset: bool


class TestDict(_TestDictBase, total=False):
    expected_file: str
    output_file: str


class Test(TypedDict):
    title: str
    stdin: str
    stdout: str
    subset: bool
    expected_file: Optional[str]
    output_file: Optional[str]


class Classification(TypedDict):
    name: str
    identifier: str
    path: str
