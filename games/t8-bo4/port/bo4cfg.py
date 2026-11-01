"""Shared paths for the port scripts. Set BO4_WORK (work folder, subfolders as in the old layout: bo3bod_port, bo4_recon, c2m) and BO3_TOOLS (Mod Tools folder) as environment variables."""
import os

WORK = os.environ.get("BO4_WORK", r"C:\work")
TOOLS = os.environ.get("BO3_TOOLS", r"C:\Program Files (x86)\Steam\steamapps\common\Call of Duty Black Ops III 455130")
GAME = os.environ.get("BO3_GAME", r"C:\Program Files (x86)\Steam\steamapps\common\Call of Duty Black Ops III")


def W(*rel):
    return os.path.join(WORK, *rel)


def T(*rel):
    return os.path.join(TOOLS, *rel)
