from typing import TYPE_CHECKING

from flask import Response
from webargs.flaskparser import use_kwargs

from rotkehlchen.api.v1.common_resources import BaseMethodView
from rotkehlchen.api.v1.schemas import (
    AccountTokenBalanceSchema,
    AddressesInteraction,
    NativeAssetTransfer,
    TokenTransfer,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset, EvmToken
    from rotkehlchen.types import ChainID, ChecksumEvmAddress, FVal


class PrepareTokenTransferResource(BaseMethodView):

    post_schema = TokenTransfer()

    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            from_address: 'ChecksumEvmAddress',
            to_address: 'ChecksumEvmAddress',
            token: 'EvmToken',
            amount: 'FVal',
    ) -> Response:
        return self.rest_api.prepare_token_transfer(
            from_address=from_address,
            to_address=to_address,
            blockchain=token.chain_id.to_blockchain(),
            token=token,
            amount=amount,
        )


class PrepareNativeTransferResource(BaseMethodView):

    post_schema = NativeAssetTransfer()

    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            from_address: 'ChecksumEvmAddress',
            to_address: 'ChecksumEvmAddress',
            chain: 'ChainID',
            amount: 'FVal',
    ) -> Response:
        return self.rest_api.prepare_native_transfer(
            from_address=from_address,
            to_address=to_address,
            chain=chain,
            amount=amount,
        )


class AddressesInteractedResource(BaseMethodView):

    post_schema = AddressesInteraction()

    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            from_address: 'ChecksumEvmAddress',
            to_address: 'ChecksumEvmAddress',
    ) -> Response:
        return self.rest_api.addresses_interacted_before(
            from_address=from_address,
            to_address=to_address,
        )


class AccountTokenBalanceResource(BaseMethodView):
    post_schema = AccountTokenBalanceSchema()

    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            asset: 'CryptoAsset',
            evm_chain: 'ChainID',
            address: 'ChecksumEvmAddress',
            async_query: bool,
    ) -> Response:
        return self.rest_api.fetch_token_balance_for_address(
            asset=asset,
            address=address,
            evm_chain=evm_chain,
            async_query=async_query,
        )
