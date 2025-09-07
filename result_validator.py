import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def is_valid_analysis_result(result: Dict[str, Any], module_name: str) -> bool:
    """
    Validates the result from an analysis module.

    A valid result must:
    1. Not be None.
    2. Be a dictionary.
    3. Not contain a top-level 'error' key with a value.
    4. Not be an empty dictionary.

    :param result: The result dictionary from an analysis module.
    :param module_name: The name of the module for logging purposes.
    :return: True if the result is valid, False otherwise.
    """
    if result is None:
        logger.warning(f"Validation failed for '{module_name}': Result is None.")
        return False

    if not isinstance(result, dict):
        logger.warning(f"Validation failed for '{module_name}': Result is not a dictionary (type: {type(result)}).")
        return False

    if not result:
        logger.warning(f"Validation failed for '{module_name}': Result is an empty dictionary.")
        return False

    if result.get('error'):
        logger.warning(f"Validation failed for '{module_name}': Module returned an error: {result['error']}")
        return False

    # Optional: Check for at least one expected key (e.g., a score)
    # This can be made more specific if needed.
    score_keys = [key for key in result.keys() if 'score' in key]
    if not score_keys:
        logger.warning(f"Validation failed for '{module_name}': Result dictionary does not contain any 'score' key.")
        # This might be a soft failure, so we can decide to return True or False.
        # For now, we'll be strict.
        return False

    logger.info(f"Validation successful for '{module_name}'.")
    return True
