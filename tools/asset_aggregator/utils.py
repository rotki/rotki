from typing import Tuple


def choose_multiple(question: str, choices: Tuple[int]) -> int:
    """Provide the user with multiple choices of 1 - n and return the choice"""
    while 'the answer is invalid':
        reply = str(input(question)).lower().strip()
        choice = int(reply[:1])
        if choice in choices:
            return choice
