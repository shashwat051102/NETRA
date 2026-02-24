import os

import yaml

import logging

logger = logging.getLogger(__name__)

def load_yaml_dict(path):

    if not path:

        return {}

    if not os.path.exists(path):

        logger.warning("Config file not found at %s", path)

        return {}

    try:

        with open(path, "r", encoding="utf-8") as f:

            data = yaml.safe_load(f) or {}

    except Exception as e:

        logger.exception("Failed reading YAML %s: %s", path, e)

        return {}

    if not isinstance(data, dict):

        logger.warning("YAML file %s did not contain a mapping/dict — got %s. Using empty dict.", path, type(data).__name__)

        return {}

    return data
