import os
from pathlib import Path


def user_config_dir(appname: str) -> str:
    home = Path(os.path.expanduser("~"))
    return str(home / ".config" / appname)
