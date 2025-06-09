"""Async implementation of blockchain and EVM endpoints

This module provides high-performance async blockchain operations.
"""
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1', tags=['blockchain'])


# Pydantic models
class BlockchainTransactionQuery(BaseModel):
    """Parameters for blockchain transaction queries"""
    async_query: bool = Field(default=True)
    only_cache: bool = Field(default=False)
    ignore_gas: bool = Field(default=False)


class EvmTransactionQuery(BaseModel):
    """Parameters for EVM transaction queries"""
    async_query: bool = Field(default=True)
    only_cache: bool = Field(default=False)
    ignore_gas: bool = Field(default=False)
    from_timestamp: int | None = Field(default=None, ge=0)
    to_timestamp: int | None = Field(default=None, ge=0)


class EvmAccountsData(BaseModel):
    """Data for managing EVM accounts"""
    blockchain: str
    accounts: list[str]


class EthereumAirdropQuery(BaseModel):
    """Parameters for Ethereum airdrop queries"""
    async_query: bool = Field(default=True)
    addresses: list[str] | None = None


class ExternalServiceData(BaseModel):
    """Configuration for external services"""
    name: str
    api_key: str | None = None
    enabled: bool = True


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError('RestAPI injection not configured')


@router.get('/blockchains/{blockchain}/transactions', response_model=dict)
async def get_blockchain_transactions(
    blockchain: str,
    async_query: bool = Query(default=True),
    only_cache: bool = Query(default=False),
    ignore_gas: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get transactions for a specific blockchain"""
    if not async_features.is_enabled(AsyncFeature.TRANSACTIONS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Parse blockchain
        try:
            chain_id = ChainID.deserialize(blockchain)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid blockchain: {e}'),
                status_code=400,
            )

        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name=f'query_{blockchain}_transactions',
                method=rest_api.rotkehlchen.chains_aggregator.query_blockchain_transactions,
                blockchain=chain_id,
                only_cache=only_cache,
                ignore_gas=ignore_gas,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.query_blockchain_transactions,
            blockchain=chain_id,
            only_cache=only_cache,
            ignore_gas=ignore_gas,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error getting blockchain transactions: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/blockchains/{blockchain}/evm/transactions', response_model=dict)
async def get_evm_transactions(
    blockchain: str,
    async_query: bool = Query(default=True),
    only_cache: bool = Query(default=False),
    ignore_gas: bool = Query(default=False),
    from_timestamp: int | None = Query(default=None, ge=0),
    to_timestamp: int | None = Query(default=None, ge=0),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get EVM transactions for a specific blockchain"""
    if not async_features.is_enabled(AsyncFeature.TRANSACTIONS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Parse blockchain
        try:
            chain_id = ChainID.deserialize(blockchain)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid blockchain: {e}'),
                status_code=400,
            )

        # Get chain manager
        chain_manager = rest_api.rotkehlchen.chains_aggregator.get_chain_manager(chain_id)
        if not chain_manager:
            return JSONResponse(
                content=create_error_response(f'Chain {blockchain} not supported'),
                status_code=400,
            )

        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name=f'query_{blockchain}_evm_transactions',
                method=chain_manager.query_evm_transactions,
                only_cache=only_cache,
                ignore_gas=ignore_gas,
                from_timestamp=Timestamp(from_timestamp) if from_timestamp else None,
                to_timestamp=Timestamp(to_timestamp) if to_timestamp else None,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await asyncio.to_thread(
            chain_manager.query_evm_transactions,
            only_cache=only_cache,
            ignore_gas=ignore_gas,
            from_timestamp=Timestamp(from_timestamp) if from_timestamp else None,
            to_timestamp=Timestamp(to_timestamp) if to_timestamp else None,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error getting EVM transactions: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/blockchains/{blockchain}/evm/transactions/decode', response_model=dict)
async def decode_evm_transactions(
    blockchain: str,
    async_query: bool = Query(default=True),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Decode pending EVM transactions"""
    if not async_features.is_enabled(AsyncFeature.TRANSACTIONS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Parse blockchain
        try:
            chain_id = ChainID.deserialize(blockchain)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid blockchain: {e}'),
                status_code=400,
            )

        # Get chain manager
        chain_manager = rest_api.rotkehlchen.chains_aggregator.get_chain_manager(chain_id)
        if not chain_manager:
            return JSONResponse(
                content=create_error_response(f'Chain {blockchain} not supported'),
                status_code=400,
            )

        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name=f'decode_{blockchain}_transactions',
                method=chain_manager.decode_undecoded_transactions,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous decoding
        result = await asyncio.to_thread(
            chain_manager.decode_undecoded_transactions,
        )

        return create_success_response({'result': result})

    except Exception as e:
        log.error(f'Error decoding EVM transactions: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/blockchains/{blockchain}/balances', response_model=dict)
async def get_blockchain_balances(
    blockchain: str,
    async_query: bool = Query(default=True),
    ignore_cache: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get balances for a specific blockchain"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Parse blockchain
        try:
            chain_id = ChainID.deserialize(blockchain)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid blockchain: {e}'),
                status_code=400,
            )

        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name=f'query_{blockchain}_balances',
                method=rest_api.rotkehlchen.chains_aggregator.query_balances,
                blockchain=chain_id,
                ignore_cache=ignore_cache,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.query_balances,
            blockchain=chain_id,
            ignore_cache=ignore_cache,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error getting blockchain balances: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/blockchains/{blockchain}/accounts', response_model=dict)
async def get_blockchain_accounts(
    blockchain: str,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get accounts for a specific blockchain"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Parse blockchain
        try:
            chain_id = ChainID.deserialize(blockchain)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid blockchain: {e}'),
                status_code=400,
            )

        # Get accounts
        accounts = rest_api.rotkehlchen.chains_aggregator.accounts.get(chain_id, [])

        return create_success_response({
            'result': [str(account) for account in accounts],
        })

    except Exception as e:
        log.error(f'Error getting blockchain accounts: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put('/blockchains/{blockchain}/accounts', response_model=dict)
async def add_blockchain_accounts(
    blockchain: str,
    accounts_data: EvmAccountsData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add accounts for a specific blockchain"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Parse blockchain
        try:
            chain_id = ChainID.deserialize(blockchain)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid blockchain: {e}'),
                status_code=400,
            )

        # Validate addresses
        try:
            addresses = [string_to_evm_address(addr) for addr in accounts_data.accounts]
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid address: {e}'),
                status_code=400,
            )

        # Add accounts
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.add_blockchain_accounts,
            blockchain=chain_id,
            accounts=addresses,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error adding blockchain accounts: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/blockchains/{blockchain}/accounts', response_model=dict)
async def remove_blockchain_accounts(
    blockchain: str,
    accounts: list[str] = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Remove accounts for a specific blockchain"""
    if not async_features.is_enabled(AsyncFeature.BALANCES_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Parse blockchain
        try:
            chain_id = ChainID.deserialize(blockchain)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid blockchain: {e}'),
                status_code=400,
            )

        # Validate addresses
        try:
            addresses = [string_to_evm_address(addr) for addr in accounts]
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid address: {e}'),
                status_code=400,
            )

        # Remove accounts
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.remove_blockchain_accounts,
            blockchain=chain_id,
            accounts=addresses,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error removing blockchain accounts: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/airdrops', response_model=dict)
async def get_ethereum_airdrops(
    async_query: bool = Query(default=True),
    addresses: str | None = Query(default=None),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get Ethereum airdrops for addresses"""
    if not async_features.is_enabled(AsyncFeature.TRANSACTIONS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Parse addresses
        address_list = None
        if addresses:
            try:
                address_list = [string_to_evm_address(addr.strip()) for addr in addresses.split(',')]
            except Exception as e:
                return JSONResponse(
                    content=create_error_response(f'Invalid address: {e}'),
                    status_code=400,
                )

        if async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='query_ethereum_airdrops',
                method=rest_api.rotkehlchen.chains_aggregator.get_ethereum_manager().airdrops.check_airdrops,
                addresses=address_list,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.chains_aggregator.get_ethereum_manager().airdrops.check_airdrops,
            addresses=address_list,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error getting Ethereum airdrops: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/external_services', response_model=dict)
async def get_external_services(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get external service configurations"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get external services
        services = rest_api.rotkehlchen.get_external_service_configurations()

        return create_success_response(services)

    except Exception as e:
        log.error(f'Error getting external services: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put('/external_services', response_model=dict)
async def set_external_services(
    services: dict[str, Any] = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Set external service configurations"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Set external services
        result = await asyncio.to_thread(
            rest_api.rotkehlchen.set_external_service_configurations,
            services=services,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error setting external services: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']
