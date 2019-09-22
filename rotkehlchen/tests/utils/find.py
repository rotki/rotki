from typing import Any, Dict, List


def find_dict_in_list(given_list: List[Dict[str, Any]], target: Dict[str, Any]) -> bool:
    """Try to find a given dict inside a list

    Naive search but it's okay, this is just a testing utility
    """
    for entry in given_list:
        found = True
        for key, value in target.items():
            if key not in entry:
                found = False
                break

            if entry[key] != value:
                found = False
                break

        if found:
            return True

    return False
