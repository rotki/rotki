import json
from typing import Any, Dict, Optional

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport


class Graph():

    def __init__(self, url: str) -> None:
        transport = RequestsHTTPTransport(url=url)
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    def query(
            self,
            querystr: str,
            param_types: Optional[Dict[str, Any]],
            param_values: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prefix = 'query '
        if param_types is not None:
            prefix += json.dumps(param_types).replace('"', '').replace('{', '(').replace('}', ')')
        prefix += '{'
        return self.client.execute(gql(prefix + querystr), variable_values=param_values)
