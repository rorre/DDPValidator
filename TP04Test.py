import os
import random
import string
import subprocess
import sys
import time
from typing import Tuple
from pathlib import Path
import shutil

try:
    import pyautogui
    import pygetwindow
    import requests
    import zxing
    from PIL import Image
    from reprint import output
except ImportError:
    print("Cannot import dependencies. Install them with:")
    print("pip install pyautogui requests zxing Pillow reprint")
    exit()

MAX_TESTS = 10
BOX_URL = "https://d.rorre.xyz/qSUxyW5wa/python_RuNAEdVJci.png"
BOX_PATH = "box_check.png"
ERR_PATH = "err_check.png"

reader = zxing.BarCodeReader()


def download_image(url: str, path: str):
    response = requests.get(url, stream=True)

    with open(path, "wb") as f:
        for data in response.iter_content():
            f.write(data)


# https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/ean.py#L43-L47
# Taken from other project so there is no bias and is guaranteed to be correct.
def calc_check_digit(number):
    """Calculate the EAN check digit for 13-digit numbers. The number passed
    should not have the check bit included."""
    return str(
        (10 - sum((3, 1)[i % 2] * int(n) for i, n in enumerate(reversed(number)))) % 10
    )


def random_str(n: int):
    return "".join([random.choice(string.ascii_letters) for _ in range(n)])


def write_inputs(
    fpath: str,
    code: int,
    saveas_box: Tuple[int, int],
    code_box: Tuple[int, int],
):
    pyautogui.moveTo(*saveas_box)
    pyautogui.click()
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("del")
    pyautogui.write(fpath + ".eps")

    pyautogui.moveTo(*code_box)
    pyautogui.click()
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("del")
    pyautogui.write(str(code))

    pyautogui.press("enter")


def check_gui(
    fpath: str,
    expected: str,
    window_region: Tuple[int, int, int, int],
) -> Tuple[bool, str]:
    pyautogui.screenshot(fpath + ".png", region=window_region)
    result_gui = reader.decode(fpath + ".png")
    return (
        not result_gui or result_gui.format != "EAN_13" or result_gui.parsed != expected
    ), result_gui.parsed


def check_postscript(fpath: str, expected: str) -> Tuple[bool, str]:
    Image.open(fpath + ".eps").save(fpath + "-convert.png")
    result_postscript = reader.decode(fpath + "-convert.png")
    return (
        not result_postscript
        or result_postscript.format != "EAN_13"
        or result_postscript.parsed != expected
    ), result_postscript.parsed


def main():
    args = sys.argv
    if len(args) != 2:
        print(f"Usage: {args[0]} path-to-TP04")
        return

    print("!!!!!!!!!!!!!!!!!!! WARNING !!!!!!!!!!!!!!!!!!!!!!!")
    print("DO NOT touch your cursor during the process.")
    print("If something goes wrong, put your cursor to the")
    print("UPPER LEFT CORNER of the screen to abort execution.")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    while True:
        inp = input("Type 'yes' if you have read the warning: ")
        if inp.lower() == "yes":
            break
    print()

    if not os.path.exists(BOX_PATH):
        print("Test box image not found, downloading...")
        download_image(BOX_URL, BOX_PATH)

    cwd = Path(".").resolve()
    tempdir = Path("tester-tmp")
    tempdir.mkdir(exist_ok=True)
    os.chdir(tempdir)

    print("Spawning TP process...")
    tp_process = subprocess.Popen(["python", args[1]])
    time.sleep(2)
    print("--------------")

    windows = pygetwindow.getWindowsWithTitle("EAN-13")
    if not windows:
        print("ERR: Cannot find TP window.")
        print("HINT: Make sure the title has 'EAN-13'.")
        tp_process.kill()
        return

    window = windows[0]
    window_region = (window.left, window.top, window.width, window.height)
    input_boxes = list(
        pyautogui.locateAllOnScreen(str(cwd / BOX_PATH), region=window_region)
    )

    if len(input_boxes) != 2:
        print(f"ERR: Expected to find 2 input boxes, got {len(input_boxes)}.")
        print("HINT: Test data uses width=15 for Entry widgets.")
        return

    saveas_box = input_boxes[0][:2]
    code_box = input_boxes[1][:2]

    with output(output_type="dict", interval=0.1) as output_dict:
        try:
            for i in range(MAX_TESTS):
                fname = random_str(8)
                fpath = fname

                code = random.randint(10 ** 11, 10 ** 12 - 1)
                check_digit = calc_check_digit(str(code))
                result_code = str(code) + check_digit

                output_dict["Progress"] = f"{i+1}/{MAX_TESTS}"
                output_dict["Output (GUI)"] = "..."
                output_dict["Output (Postscript)"] = "..."
                output_dict["Status"] = "In progress"
                output_dict["Expected"] = result_code

                write_inputs(fpath, code, saveas_box, code_box)

                result_gui = check_gui(fpath, result_code, window_region)
                output_dict["Output (GUI)"] = result_gui[1]
                if result_gui[0]:
                    output_dict["Status"] = "FAILED"
                    break

                result_postscript = check_postscript(fpath, result_code)
                output_dict["Output (Postscript)"] = result_postscript[1]
                if result_postscript[0]:
                    output_dict["Status"] = "FAILED"
                    break
            else:
                output_dict["Status"] = "SUCCESS"

        except pyautogui.FailSafeException:
            output_dict["Status"] = "ABORTED"
            output_dict.append("Failsafe detected, ending execution...")
            pass

    tp_process.kill()
    os.chdir("..")
    time.sleep(1)
    shutil.rmtree(tempdir)


if __name__ == "__main__":
    main()
