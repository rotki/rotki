from pathlib import Path
from typing import Optional

import requests
from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.externalapis.coingecko import Coingecko


class IconManager():

    def __init__(self, data_dir: Path, coingecko: Coingecko) -> None:
        self.icons_dir = data_dir / 'icons'
        self.coingecko = coingecko
        self.icons_dir.mkdir(parents=True, exist_ok=True)

    def get_icon(
            self,
            asset: Asset, given_size: Literal['thumb', 'small', 'large'],
    ) -> Optional[bytes]:
        """Returns the byte data of the requested icon

        If the icon can't be found it returns None.

        If the icon is found cached locally it's returned directly.

        If not,all icons of the asset are queried from coingecko and cached
        locally before the requested data are returned.
        """
        if not asset.has_coingecko():
            return None

        needed_path = self.icons_dir / f'{asset.identifier}_{given_size}.png'
        if needed_path.is_file():
            with open(needed_path, 'rb') as f:
                image_data = f.read()
            return image_data

        # else query coingecko for the icons and cache all of them
        data = self.coingecko.asset_data(asset)
        for size in ('thumb', 'small', 'large'):
            url = getattr(data.images, size)
            response = requests.get(url)
            icon_path = self.icons_dir / f'{asset.identifier}_{size}.png'
            with open(icon_path, 'wb') as f:
                f.write(response.content)

        with open(needed_path, 'rb') as f:
            image_data = f.read()
        return image_data
