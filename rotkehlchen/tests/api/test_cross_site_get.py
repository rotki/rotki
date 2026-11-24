from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.constants import ONE
from rotkehlchen.db.snapshots import BALANCES_FILENAME
from rotkehlchen.tests.api.test_snapshots import (
    _populate_db_with_balances,
    _populate_db_with_location_data,
)
from rotkehlchen.tests.utils.api import api_url_for
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from pathlib import Path

    from rotkehlchen.api.server import APIServer

# what an <img> or a no-cors fetch from another site sends: fetch metadata, no Origin
CROSS_SITE_NO_CORS = {'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'no-cors'}


@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_snapshot_export_cross_site_other_forms(
        rotkehlchen_api_server: APIServer,
        tmp_path: Path,
) -> None:
    """The snapshot export guard holds for HEAD and for the route without a timestamp.

    Flask answers HEAD with the view's GET, and `/snapshots` takes the timestamp from
    the query string, so both reach the same export.
    """
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with db.user_write() as cursor:
        _populate_db_with_balances(cursor, db, ts := ts_now())
        _populate_db_with_location_data(cursor, db, ts)

    for method, url in (
        (requests.head, api_url_for(
            rotkehlchen_api_server,
            'per_timestamp_db_snapshots_resource',
            timestamp=ts,
            path=str(tmp_path),
            action='export',
        )),
        (requests.get, api_url_for(
            rotkehlchen_api_server,
            'dbsnapshotsresource',
            timestamp=ts,
            path=str(tmp_path),
            action='export',
        )),
    ):
        response = method(url, headers=CROSS_SITE_NO_CORS)
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not (tmp_path / BALANCES_FILENAME).exists()

        # control: the same request from a non-browser client reaches the export
        response = method(url)
        assert response.status_code == HTTPStatus.OK
        assert (tmp_path / BALANCES_FILENAME).exists()
        (tmp_path / BALANCES_FILENAME).unlink()


@pytest.mark.parametrize('method', ['get', 'head'])
def test_report_export_cross_site(
        rotkehlchen_api_server: APIServer,
        tmp_path: Path,
        method: str,
) -> None:
    """A cross-site GET or HEAD can't reach the PnL report export, which writes to disk."""
    url = api_url_for(
        rotkehlchen_api_server,
        'accountingreportexportresource',
        report_id=1,
        directory_path=str(tmp_path),
    )
    response = requests.request(method, url, headers=CROSS_SITE_NO_CORS)
    assert response.status_code == HTTPStatus.FORBIDDEN

    # control: without fetch metadata the request reaches the view (no report: 409)
    response = requests.request(method, url)
    assert response.status_code == HTTPStatus.CONFLICT
