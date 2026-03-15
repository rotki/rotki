from http import HTTPStatus
from typing import Any


def wrap_in_fail_result(message: str, status_code: HTTPStatus | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {'result': None, 'message': message}
    if status_code:
        result['status_code'] = status_code

    return result
