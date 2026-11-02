from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from rotkehlchen.errors.cause import FailureCause  # noqa: TC001  # dataclass field type
from rotkehlchen.serialization.serialize import process_result


@dataclass(frozen=True, slots=True)
class OkResult:
    """A request that succeeded.

    `message` carries a note for a success the user should still read, such as a restored
    backup. `status` is 200 unless the success needs another code, such as the 202 of a
    bank connection that waits for a second factor.
    """
    result: Any
    message: str = ''
    status: HTTPStatus = HTTPStatus.OK


@dataclass(frozen=True, slots=True)
class FailResult:
    """A request that failed, with the cause that says whether retrying can help.

    `result` is set only for the few failures that hand data back with the error, such as
    the report an accounting error belongs to.
    """
    message: str
    status: HTTPStatus
    cause: FailureCause
    result: Any = None


type ApiResult = OkResult | FailResult


def serialize_result(result: ApiResult) -> dict[str, Any]:
    """The wire form of a result. Only a failure carries a cause."""
    serialized: dict[str, Any] = {'result': result.result, 'message': result.message}
    if isinstance(result, FailResult):
        serialized['cause'] = result.cause
    return process_result(serialized)
