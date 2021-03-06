import ctypes
import os
import platform
import random
import shutil
import string
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple, Union

try:
    import cv2
    import numpy as np
    import pyautogui
    import pygetwindow
    import requests
    import zxing
    from PIL import Image
    from reprint import output
except ImportError:
    print("Cannot import dependencies. Install them with:")
    print("  pip install pyautogui requests zxing Pillow reprint opencv-python")
    exit(1)

if sys.platform.startswith("win"):
    for binary in ("gswin32c", "gswin64c", "gs"):
        if shutil.which(binary) is not None:
            has_ghostscript = True
            break
    else:
        print("Cannot find ghostscript in PATH, skipping postscript check.")
        has_ghostscript = False

# fmt: off
DISALLOWED_CHARS = [
    "/", "<", ">", ":", '"', "\\", "|", "?", "*"
]
DISALLOWED_NAMES = [
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
]
# fmt: on

ERR_URL = "https://d.rorre.xyz/HxifAQKX5/python_iAZcyBZK5C.png"
ERR_PATH = "err_check.png"

Point = Tuple[int, int]
Rect = Tuple[int, int, int, int]

user32 = ctypes.windll.user32
SM_CYFRAME = 32
SM_CYCAPTION = 4
SM_CXPADDEDBORDER = 92

reader = zxing.BarCodeReader()
cwd = Path(".").resolve()
box_absolute_path = str(cwd.resolve() / ERR_PATH)


class FailedCheck(Exception):
    pass


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


def write_box(path: Point, text: str):
    pyautogui.moveTo(*path)
    pyautogui.click()
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("del")
    pyautogui.write(text)


def write_inputs(
    fpath: str,
    code: Union[int, str],
    saveas_point: Point,
    code_point: Point,
):
    write_box(saveas_point, fpath)
    write_box(code_point, str(code))
    pyautogui.press("enter")


def check_gui(
    fpath: str,
    expected: str,
    window_region: Rect,
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


def normalize_square(rect: Rect, window_region: Rect) -> Rect:
    return (
        rect[0] + window_region[0],
        rect[1] + window_region[1],
        rect[2],
        rect[3],
    )


def find_boxes(window_region: Rect) -> List[Rect]:
    im = pyautogui.screenshot(region=window_region)

    im_cv2 = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY)
    _, thrash = cv2.threshold(im_cv2, 240, 255, cv2.CHAIN_APPROX_NONE)
    contours, _ = cv2.findContours(thrash, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    rects = []
    for contour in contours:
        # Approximate number of sides in contours
        sides = cv2.approxPolyDP(contour, 0.01 * cv2.arcLength(contour, True), True)
        # Not a rectangle, so whatever
        if len(sides) != 4:
            continue
        rect = normalize_square(cv2.boundingRect(sides), window_region)
        rects.append(rect)
    rects.sort(key=lambda x: x[1])

    used_rects = rects[-3:]
    return used_rects


def check_failed(
    file_input: str,
    code_input: Union[int, str],
    message: str,
    saveas_point: Point,
    code_point: Point,
):
    write_inputs(file_input, code_input, saveas_point, code_point)
    time.sleep(0.25)
    err_location = pyautogui.locateOnScreen(box_absolute_path)
    if not err_location:
        raise FailedCheck(message)
    pyautogui.press("enter")


def check_passing(
    file_input: str,
    code_input: Union[int, str],
    saveas_point: Point,
    code_point: Point,
):
    write_inputs(file_input, code_input, saveas_point, code_point)
    time.sleep(0.25)
    err_location = pyautogui.locateOnScreen(box_absolute_path)
    if err_location:
        raise FailedCheck("Unexpected error is detected. Output should be correct.")


def do_error_check(
    saveas_point: Point,
    code_point: Point,
):
    check_failed(
        "sample.eps",
        1,
        "Code consisting of non 12-digit characters should raise error.",
        saveas_point,
        code_point,
    )
    check_failed(
        "sample.eps",
        1234567891231,
        "Code consisting of non 12-digit characters should raise error.",
        saveas_point,
        code_point,
    )
    check_failed(
        "sample.eps",
        12345678912,
        "Code consisting of non 12-digit characters should raise error.",
        saveas_point,
        code_point,
    )
    check_failed(
        "sample.eps",
        "",
        "Empty code should raise error.",
        saveas_point,
        code_point,
    )
    check_failed(
        "",
        123456789123,
        "Empty save as field should raise error.",
        saveas_point,
        code_point,
    )
    check_failed(
        "sample.jpg",
        123456789123,
        "Invalid extension should raise error.",
        saveas_point,
        code_point,
    )
    for char in DISALLOWED_CHARS:
        check_failed(
            f"samp{char}le.eps",
            123456789123,
            "Banned char should raise error.",
            saveas_point,
            code_point,
        )
    for name in DISALLOWED_NAMES:
        check_failed(
            f"{name}.sample.eps",
            123456789123,
            "Banned name should raise error.",
            saveas_point,
            code_point,
        )

    for name in DISALLOWED_NAMES:
        check_passing(f"sample.{name}.eps", 123456789123, saveas_point, code_point)
    check_passing("sample.eps", 123456789123, saveas_point, code_point)
    check_passing("sample.ps", 123456789123, saveas_point, code_point)


def main():
    if not (platform.system() == "Windows" and platform.release() == "10"):
        print("This script only works in Windows 10.")
        exit(1)

    args = sys.argv
    if not 2 <= len(args) <= 4:
        print(f"Usage: {args[0]} [--skip-validation] path-to-TP04 <number-of-tests>")
        print("number-of-tests defaults to 10.")
        return

    skip_validation = False
    if args[1] == "--skip-validation":
        skip_validation = True
        args.pop(1)

    if len(args) == 3:
        MAX_TESTS = int(args[2])
    else:
        MAX_TESTS = 10

    if not os.path.exists(ERR_PATH):
        download_image(ERR_URL, ERR_PATH)

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

    tempdir = Path("tester-tmp")
    tempdir.mkdir(exist_ok=True)
    os.chdir(tempdir)

    print("Spawning TP process...")
    tp_process = subprocess.Popen(["python", args[1]])
    time.sleep(2)

    windows = pygetwindow.getWindowsWithTitle("EAN-13")
    if not windows:
        print("ERR: Cannot find TP window.")
        print("HINT: Make sure the title has 'EAN-13'.")
        tp_process.kill()
        return

    print("Locating input boxes and barcode box...")
    window = windows[0]
    title_height = (
        user32.GetSystemMetrics(SM_CYFRAME)
        + user32.GetSystemMetrics(SM_CYCAPTION)
        + user32.GetSystemMetrics(SM_CXPADDEDBORDER)
    )
    actual_top = window.top + title_height
    actual_height = window.height - title_height

    window_region = (window.left, actual_top, window.width, actual_height)
    input_boxes = find_boxes(window_region)

    if len(input_boxes) != 3:
        print(f"ERR: Expected to find 3 boxes, got {len(input_boxes)}.")
        print("HINT: Test data uses width=15 for Entry widgets.")
        return

    saveas_box = input_boxes[0]
    code_box = input_boxes[1]
    barcode_box = input_boxes[2]

    saveas_point = (
        saveas_box[0] + saveas_box[2] // 4,
        saveas_box[1] + saveas_box[3] // 4,
    )
    code_point = (
        code_box[0] + code_box[2] // 4,
        code_box[1] + code_box[3] // 4,
    )

    print("Save as box:", saveas_box)
    print("Code box:", code_box)
    print("Barcode box:", barcode_box)
    print("--------------")

    with output(output_type="dict") as output_dict:
        try:
            if not skip_validation:
                output_dict["Progress"] = "Checking input validations..."
                output_dict["Status"] = "In progress"
                do_error_check(saveas_point, code_point)

            for i in range(MAX_TESTS):
                fname = random_str(8)
                fpath = fname

                code = random.randint(10 ** 11, 10 ** 12 - 1)
                check_digit = calc_check_digit(str(code))
                result_code = str(code) + check_digit

                output_dict["Progress"] = f"{i+1}/{MAX_TESTS}"
                output_dict["Output (GUI)"] = "..."
                if has_ghostscript:
                    output_dict["Output (Postscript)"] = "..."
                output_dict["Expected"] = result_code

                write_inputs(fpath + ".eps", code, saveas_point, code_point)

                result_gui = check_gui(fpath, result_code, barcode_box)
                output_dict["Output (GUI)"] = result_gui[1]
                if result_gui[0]:
                    output_dict["Status"] = "FAILED"
                    break

                if has_ghostscript:
                    result_postscript = check_postscript(fpath, result_code)
                    output_dict["Output (Postscript)"] = result_postscript[1]
                    if result_postscript[0]:
                        output_dict["Status"] = "FAILED"
                        break
            else:
                output_dict["Status"] = "SUCCESS"
        except FailedCheck as e:
            output_dict["Status"] = "FAILED"
            output_dict.append(str(e))
        except pyautogui.FailSafeException:
            output_dict["Status"] = "ABORTED"
            output_dict.append("Failsafe detected, ending execution...")
            pass

    tp_process.kill()
    os.chdir(cwd)
    time.sleep(1)
    shutil.rmtree(tempdir)


if __name__ == "__main__":
    main()
