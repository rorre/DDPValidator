import sys

BASE_RESOURCES_URL = "https://raw.githubusercontent.com/rorre/DDPValidator/main/data"
GITHUB_URL = "https://api.github.com/repos/rorre/DDPValidator/releases/latest"
IS_FROZEN = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
