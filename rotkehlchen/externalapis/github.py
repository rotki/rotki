from json.decoder import JSONDecodeError
from typing import Dict, Tuple

import requests

from rotkehlchen.errors import RemoteError
from rotkehlchen.utils.serialization import rlk_jsonloads_dict


class Github():

    def __init__(self) -> None:
        self.prefix = 'https://api.github.com/'

    def _query(self, path: str) -> Dict:
        """
        May raise:
        - RemoteError if there is a problem querying Github
        """
        try:
            response = requests.get(f'{self.prefix}{path}')
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Failed to query Github: {str(e)}') from e

        if response.status_code != 200:
            raise RemoteError(
                f'Github API request {response.url} for {path} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = rlk_jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(f'Github returned invalid JSON response: {response.text}') from e
        return json_ret

    def get_latest_release(self) -> Tuple[str, str]:
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
