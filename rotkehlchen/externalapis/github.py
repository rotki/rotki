import json
from json.decoder import JSONDecodeError

import requests

from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.misc import RemoteError


class Github:

    def __init__(self) -> None:
        self.prefix = 'https://api.github.com/'

    def _query(self, path: str) -> dict:
        """
        May raise:
        - RemoteError if there is a problem querying Github
        """
        try:
            response = requests.get(url=f'{self.prefix}{path}', timeout=DEFAULT_TIMEOUT_TUPLE)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to query Github: {e!s}') from e

        if response.status_code != 200:
            raise RemoteError(
                f'Github API request {response.url} for {path} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:  # TODO: Fix this avoiding circular import in a more elegant way
            json_ret = json.loads(response.text)  # not using jsonloads_dict due to circular import
            if not isinstance(json_ret, dict):
                raise JSONDecodeError(msg='Returned json is not a dict', doc='{}', pos=0)
        except JSONDecodeError as e:
            raise RemoteError(f'Github returned invalid JSON response: {response.text}') from e
        return json_ret

    def get_latest_release(self) -> tuple[str, str]:
        """Returns the latest rotkehlchen release version

        In success returns a tuple (version_tag, version_download_url)
        Will raise RemoteError in all kind of errors
        """
        response = self._query('repos/rotki/rotki/releases/latest')
        if 'tag_name' not in response:
            raise RemoteError(
                'Github latest release did not contain a "tag_name" entry in the response',
            )
        if 'html_url' not in response:
            raise RemoteError(
                'Github latest release did not contain a "html_url" entry in the response',
            )
        return response['tag_name'], response['html_url']
