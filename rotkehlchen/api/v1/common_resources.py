from typing import TYPE_CHECKING, Any

from flask.views import MethodView

if TYPE_CHECKING:
    from rotkehlchen.api.rest import RestAPI


class BaseMethodView(MethodView):

    def __init__(self, rest_api_object: 'RestAPI', **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.rest_api = rest_api_object
