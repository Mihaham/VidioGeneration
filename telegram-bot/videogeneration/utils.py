from loguru import logger
import os
from pathlib import Path
def get_next_free_path(dir: str, prefix : str = "image_", suffix = ".png") -> int:
    answer = 0
    while os.path.exists(potential_path := f"{dir}/{prefix}{answer}{suffix}"):
        answer += 1
    logger.debug(f"Next free path is {potential_path}")
    return potential_path

def create_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)
    logger.debug(f"Directory created at {path}")