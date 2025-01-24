import filecmp
import shutil
import urllib.parse
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.constants.misc import (
    ASSETIMAGESDIR_NAME,
    CUSTOMASSETIMAGESDIR_NAME,
    IMAGESDIR_NAME,
)
from rotkehlchen.icons import ALLOWED_ICON_EXTENSIONS
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.constants import A_DOGE, A_GNO
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('start_with_logged_in_user', [False])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('file_upload', [True, False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upload_custom_icon(
        rotkehlchen_api_server: 'APIServer',
        file_upload: bool,
        data_dir: Path,
    ) -> None:
    """Test that uploading custom icon works"""
    root_path = Path(__file__).resolve().parent.parent.parent.parent
    filepath = root_path / 'frontend' / 'app' / 'public' / 'assets' / 'images' / 'protocols' / 'kraken.svg'  # noqa: E501
    gno_id_quoted = urllib.parse.quote_plus(A_GNO.identifier)

    if file_upload:
        with open(filepath, 'rb') as infile:
            response = requests.post(
                api_url_for(
                    rotkehlchen_api_server,
                    'asseticonsresource',
                ),
                files={'file': infile},
                data={'asset': gno_id_quoted},
            )
    else:
        json_data = {'file': str(filepath), 'asset': gno_id_quoted}
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'asseticonsresource',
            ), json=json_data,
        )

    result = assert_proper_sync_response_with_result(response)
    assert result == {'identifier': A_GNO.identifier}
    uploaded_icon = data_dir / IMAGESDIR_NAME / ASSETIMAGESDIR_NAME / CUSTOMASSETIMAGESDIR_NAME / f'{gno_id_quoted}.svg'  # noqa: E501
    assert uploaded_icon.is_file()
    assert filecmp.cmp(uploaded_icon, filepath)


@pytest.mark.parametrize('start_with_logged_in_user', [False])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('file_upload', [True, False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_upload_custom_icon_errors(rotkehlchen_api_server: 'APIServer', file_upload: bool) -> None:
    """Test that common error handling for uploading custom icons"""
    root_path = Path(__file__).resolve().parent.parent.parent.parent
    filepath = root_path / 'frontend' / 'app' / 'public' / 'assets' / 'images' / 'protocols' / 'kraken.svg'  # noqa: E501

    # Let's also try to upload a file without the csv prefix
    with TemporaryDirectory() as temp_directory:
        bad_filepath = Path(temp_directory) / 'somefile.bad'
        shutil.copyfile(filepath, bad_filepath)
        if file_upload:
            with open(bad_filepath, 'rb') as infile:
                response = requests.post(
                    api_url_for(
                        rotkehlchen_api_server,
                        'asseticonsresource',
                    ),
                    json={'asset': urllib.parse.quote_plus(A_GNO.identifier)},
                    files={'file': infile},
                )
        else:
            json_data = {
                'file': str(bad_filepath),
                'asset': urllib.parse.quote_plus(A_GNO.identifier),
            }
            response = requests.put(
                api_url_for(
                    rotkehlchen_api_server,
                    'asseticonsresource',
                ), json=json_data,
            )

    assert_error_response(
        response=response,
        contained_in_msg=f'does not end in any of {",".join(ALLOWED_ICON_EXTENSIONS)}',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_refresh_icon(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that checks refreshing the icon of an asset works."""
    # add icon for an asset
    icon_manager = rotkehlchen_api_server.rest_api.rotkehlchen.icon_manager
    root_path = Path(__file__).resolve().parent.parent.parent.parent
    sample_filepath = root_path / 'frontend' / 'app' / 'public' / 'assets' / 'images' / 'protocols' / 'kraken.svg'  # noqa: E501
    icon_filepath = icon_manager.icons_dir / 'DOGE_small.png'
    shutil.copyfile(sample_filepath, icon_filepath)

    now = ts_now()
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'asseticonsresource',
        ),
        json={'asset': urllib.parse.quote_plus(A_DOGE.identifier)},
    )
    assert_simple_ok_response(response)
    assert icon_filepath.stat().st_ctime > now
