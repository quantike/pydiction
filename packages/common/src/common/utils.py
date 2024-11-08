from pathlib import Path
import yaml
from typing import Dict


def load_from_yaml(filename: Path) -> Dict:
    """
    Loads content from a yaml file given a filename.

    We make the assumption that these files sit at the repository level.
    """
    with open(filename, "r") as file:
        content = yaml.safe_load(file)

    return content
