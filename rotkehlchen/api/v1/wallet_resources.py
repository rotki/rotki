from flask import Response
from webargs.flaskparser import use_kwargs

from rotkehlchen.api.v1.common_resources import BaseMethodView
from rotkehlchen.api.v1.schemas import AddressesInteraction, NativeAssetTransfer, TokenTransfer
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.types import ChecksumEvmAddress, FVal, SupportedBlockchain


class PrepareTokenTransferResource(BaseMethodView):

    post_schema = TokenTransfer()

    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            token: EvmToken,
            amount: FVal,
    ) -> Response:
        return self.rest_api.prepare_token_transfer(
            from_address=from_address,
            to_address=to_address,
            token=token,
            amount=amount,
        )


class PrepareNativeTransferResource(BaseMethodView):

    post_schema = NativeAssetTransfer()

    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            blockchain: SupportedBlockchain,
            amount: FVal,
    ) -> Response:
        return self.rest_api.prepare_native_transfer(
            from_address=from_address,
            to_address=to_address,
            blockchain=blockchain,
            amount=amount,
        )


class AddressesInteractedResource(BaseMethodView):

    post_schema = AddressesInteraction()

    @use_kwargs(post_schema, location='json_and_view_args')
    def post(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
    ) -> Response:
        return self.rest_api.addresses_interacted_before(
            from_address=from_address,
            to_address=to_address,
        )
