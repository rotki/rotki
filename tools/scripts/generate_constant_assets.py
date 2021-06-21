from pathlib import Path
from typing import Dict

from rotkehlchen.config import default_data_directory
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.utils.misc import timestamp_to_date, ts_now


class ContextManager():
    """Manages the parsing context of the assets template"""

    def __init__(self) -> None:
        self.id_to_variable: Dict[str, str] = {}
        self.globaldb = GlobalDBHandler(default_data_directory())

    def add_asset_initialization(self, var_name: str, identifier: str) -> str:
        generated_text = ''
        asset_data = self.globaldb.get_asset_data(identifier=identifier, form_with_incomplete_data=False)  # noqa: E501
        var_forked = 'None'
        if asset_data.forked:
            if asset_data.forked in self.id_to_variable:
                var_forked = self.id_to_variable[asset_data.forked]
            else:
                var_forked = f'{identifier.upper()}_forked'
                generated_text += self.add_asset_initialization(var_forked, asset_data.forked.identifier)  # noqa: E501
        var_swappedfor = 'None'
        if asset_data.swapped_for:
            if asset_data.swapped_for in self.id_to_variable:
                var_swappedfor = self.id_to_variable[asset_data.swapped_for]
            else:
                var_swappedfor = f'{identifier.upper()}_swappedfor'
                generated_text += self.add_asset_initialization(var_swappedfor, asset_data.swapped_for.identifier)  # noqa:E501

        name = f'"{asset_data.name}"' if asset_data.name else None
        symbol = f'\'{asset_data.symbol}\'' if asset_data.symbol else None
        started = f'Timestamp({asset_data.started})' if asset_data.started else None
        coingecko = f'\'{asset_data.coingecko}\'' if asset_data.coingecko else None
        cryptocompare = f'\'{asset_data.cryptocompare}\'' if asset_data.cryptocompare else None
        generated_text += (
            f'{var_name} = Asset.initialize(\n'
            f'    identifier=\'{identifier}\',\n'
            f'    asset_type=AssetType.{asset_data.asset_type.name},\n'
            f'    name={name},\n'
            f'    symbol={symbol},\n'
            f'    started={started},\n'
            f'    forked={var_forked},\n'
            f'    swapped_for={var_swappedfor},\n'
            f'    coingecko={coingecko},\n'
            f'    cryptocompare={cryptocompare},\n'
            f')\n'
            f'CONSTANT_ASSETS.append({var_name})\n'
        )

        if identifier in self.id_to_variable:
            raise ValueError(f'Asset with identifier {identifier} and var_name {var_name} is defined twice')  # noqa: E501
        self.id_to_variable[identifier] = var_name
        return generated_text

    def add_ethtoken_initialization(self, var_name: str, address: str) -> str:
        generated_text = ''
        token = self.globaldb.get_ethereum_token(address=address)
        var_swappedfor = 'None'
        if token.swapped_for:
            if token.swapped_for in self.id_to_variable:
                var_swappedfor = self.id_to_variable[token.swapped_for]
            else:
                var_swappedfor = f'{strethaddress_to_identifier(address).upper()}_swappedfor'
                generated_text += self.add_asset_initialization(var_swappedfor, token.swapped_for.identifier)  # noqa: E501

        name = f'"{token.name}"' if token.name else None
        symbol = f'\'{token.symbol}\'' if token.symbol else None
        started = f'Timestamp({token.started})' if token.started else None
        coingecko = f'\'{token.coingecko}\'' if token.coingecko else None
        cryptocompare = f'\'{token.cryptocompare}\'' if token.cryptocompare else None
        protocol = f'\'{token.protocol}\'' if token.protocol else None
        if token.underlying_tokens is not None:
            raise ValueError(
                f'Found token {address} with underlying tokens. Not supported '
                f'at constants asset generation yet. Can implement when needed.',
            )
        generated_text += (
            f'{var_name} = EthereumToken.initialize(\n'
            f'    address=string_to_ethereum_address(\'{address}\'),\n'
            f'    decimals={token.decimals},\n'
            f'    name={name},\n'
            f'    symbol={symbol},\n'
            f'    started={started},\n'
            f'    swapped_for={var_swappedfor},\n'
            f'    coingecko={coingecko},\n'
            f'    cryptocompare={cryptocompare},\n'
            f'    protocol={protocol},\n'
            f')\n'
            f'CONSTANT_ASSETS.append({var_name})\n'
        )
        identifier = strethaddress_to_identifier(address)
        if identifier in self.id_to_variable:
            raise ValueError(f'Token with identifier {identifier} and varname {var_name} is defined twice')  # noqa: E501
        self.id_to_variable[identifier] = var_name
        return generated_text


def main() -> None:
    """Goes through the assets template, reads the built-in assets DB and generates
    assets.py with initialization of all constant assets"""
    root_dir = Path(__file__).resolve().parent.parent.parent
    constants_dir = root_dir / 'rotkehlchen' / 'constants'
    template_file = constants_dir / 'assets.py.template'
    date = timestamp_to_date(ts_now())
    generated_text = (
        f'# This python file was generated automatically by\n'
        f'# {__file__} at {date}.\n'
        f'# Do not edit manually!\n'
        f'\n'
    )
    ctx = ContextManager()
    with open(template_file, 'r') as f:
        for line in f:
            line = line.strip('\n\r')
            if 'Asset(\'' in line:
                initial_split = line.split(' = Asset(\'')
                var_name = initial_split[0]
                identifier = initial_split[1].split('\'')[0]
                generated_text += ctx.add_asset_initialization(var_name, identifier)
                continue

            if 'EthereumToken(\'' in line:
                initial_split = line.split(' = EthereumToken(\'')
                var_name = initial_split[0]
                identifier = initial_split[1].split('\'')[0]
                generated_text += ctx.add_ethtoken_initialization(var_name, identifier)
                continue

            # else just copy text
            generated_text += line + '\n'

    assets_file = constants_dir / 'assets.py'
    with open(assets_file, 'w') as f:
        f.write(generated_text)

    print('constants/assets.py generated succesfully!')


if __name__ == "__main__":
    main()
