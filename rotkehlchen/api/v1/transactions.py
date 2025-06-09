"""Async implementation of transaction query endpoints

This provides high-performance async transaction querying.
"""
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.chain.ethereum.utils import deserialize_evm_address
from rotkehlchen.db.async_handler import AsyncDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.async_manager import AsyncTaskManager
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1', tags=['transactions'])


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError('RestAPI injection not configured')


async def get_async_db() -> AsyncDBHandler:
    """Get async database handler - will be injected by the app"""
    raise NotImplementedError('AsyncDBHandler injection not configured')


async def get_task_manager() -> AsyncTaskManager:
    """Get async task manager - will be injected by the app"""
    raise NotImplementedError('AsyncTaskManager injection not configured')


@router.get('/blockchains/evm/transactions', response_model=dict)
async def query_evm_transactions(
    # Chain filter
    evm_chain: str | None = Query(None),
    # Address filter
    address: str | None = Query(None),
    # Time filters
    from_timestamp: int | None = Query(None, ge=0),
    to_timestamp: int | None = Query(None, ge=0),
    # Pagination
    limit: int = Query(500, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    # Ordering
    order_by_field: str = Query('timestamp', regex='^(timestamp|gas_price|gas_used|value)$'),
    order_by_ascending: bool = Query(False),
    # Async query
    async_query: bool = Query(False),
    # Dependencies
    rest_api: RestAPI = Depends(get_rest_api),
    async_db: AsyncDBHandler = Depends(get_async_db),
    task_manager: AsyncTaskManager = Depends(get_task_manager),
):
    """Query EVM transactions with high performance async implementation"""
    if not async_features.is_enabled(AsyncFeature.TRANSACTIONS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Validate inputs
        chain = ChainID(evm_chain) if evm_chain else None
        validated_address: ChecksumEvmAddress | None = None
        if address:
            validated_address = deserialize_evm_address(address)

        # Handle async query
        if async_query:
            # Spawn async task
            async def _query_transactions():
                return await _do_query_transactions(
                    async_db=async_db,
                    chain=chain,
                    address=validated_address,
                    from_ts=from_timestamp,
                    to_ts=to_timestamp,
                    limit=limit,
                    offset=offset,
                    order_by=order_by_field,
                    ascending=order_by_ascending,
                )

            task = await task_manager.spawn_and_track(
                task_name=f'query_evm_transactions_{chain}_{address}',
                coro=_query_transactions(),
                timeout=120.0,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await _do_query_transactions(
            async_db=async_db,
            chain=chain,
            address=validated_address,
            from_ts=from_timestamp,
            to_ts=to_timestamp,
            limit=limit,
            offset=offset,
            order_by=order_by_field,
            ascending=order_by_ascending,
        )

        return create_success_response(result)

    except ValueError as e:
        return JSONResponse(
            content=create_error_response(f'Invalid parameters: {e}'),
            status_code=400,
        )
    except Exception as e:
        log.error(f'Error querying transactions: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


async def _do_query_transactions(
    async_db: AsyncDBHandler,
    chain: ChainID | None,
    address: ChecksumEvmAddress | None,
    from_ts: Timestamp | None,
    to_ts: Timestamp | None,
    limit: int,
    offset: int,
    order_by: str,
    ascending: bool,
) -> dict[str, Any]:
    """Execute the actual transaction query using async database"""
    # Build query
    query_parts = []
    params = []

    base_query = """
        SELECT
            tx_hash, chain_id, timestamp, block_number, from_address, to_address,
            value, gas, gas_price, gas_used, input_data, nonce
        FROM ethereum_transactions
        WHERE 1=1
    """

    if chain:
        query_parts.append('chain_id = ?')
        params.append(chain.value)

    if address:
        query_parts.append('(from_address = ? OR to_address = ?)')
        params.extend([address, address])

    if from_ts is not None:
        query_parts.append('timestamp >= ?')
        params.append(from_ts)

    if to_ts is not None:
        query_parts.append('timestamp <= ?')
        params.append(to_ts)

    if query_parts:
        base_query += ' AND ' + ' AND '.join(query_parts)

    # Count total
    count_query = f'SELECT COUNT(*) FROM ({base_query})'
    async with async_db.async_conn.read_ctx() as cursor:
        await cursor.execute(count_query, tuple(params) if params else None)
        total_count = (await cursor.fetchone())[0]

    # Add ordering and pagination
    direction = 'ASC' if ascending else 'DESC'
    base_query += f' ORDER BY {order_by} {direction}'
    base_query += f' LIMIT {limit} OFFSET {offset}'

    # Execute main query
    async with async_db.async_conn.read_ctx() as cursor:
        await cursor.execute(base_query, tuple(params) if params else None)
        rows = await cursor.fetchall()

    # Format results
    entries = [{
            'tx_hash': row[0],
            'chain_id': row[1],
            'timestamp': row[2],
            'block_number': row[3],
            'from_address': row[4],
            'to_address': row[5],
            'value': str(row[6]),
            'gas': str(row[7]),
            'gas_price': str(row[8]),
            'gas_used': str(row[9]),
            'input_data': row[10],
            'nonce': row[11],
        } for row in rows]

    return {
        'entries': entries,
        'entries_found': total_count,
        'entries_limit': limit,
        'entries_total': total_count,
    }


@router.get('/blockchains/evm/transactions/{tx_hash}', response_model=dict)
async def get_transaction_details(
    tx_hash: str,
    evm_chain: str = Query(...),
    async_db: AsyncDBHandler = Depends(get_async_db),
):
    """Get detailed information about a specific transaction"""
    if not async_features.is_enabled(AsyncFeature.TRANSACTIONS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        chain = ChainID(evm_chain)

        # Query transaction
        async with async_db.async_conn.read_ctx() as cursor:
            await cursor.execute(
                """
                SELECT
                    tx_hash, chain_id, timestamp, block_number, from_address, to_address,
                    value, gas, gas_price, gas_used, input_data, nonce, status
                FROM ethereum_transactions
                WHERE tx_hash = ? AND chain_id = ?
                """,
                (tx_hash, chain.value),
            )
            row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail='Transaction not found')

        # Format result
        transaction = {
            'tx_hash': row[0],
            'chain_id': row[1],
            'timestamp': row[2],
            'block_number': row[3],
            'from_address': row[4],
            'to_address': row[5],
            'value': str(row[6]),
            'gas': str(row[7]),
            'gas_price': str(row[8]),
            'gas_used': str(row[9]),
            'input_data': row[10],
            'nonce': row[11],
            'status': row[12],
        }

        # Could also query decoded events here

        return create_success_response(transaction)

    except ValueError as e:
        return JSONResponse(
            content=create_error_response(f'Invalid chain: {e}'),
            status_code=400,
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f'Error getting transaction details: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/blockchains/evm/transactions/decode', response_model=dict)
async def decode_transactions(
    tx_hashes: list[str] = Query(...),
    evm_chain: str = Query(...),
    ignore_cache: bool = Query(False),
    async_db: AsyncDBHandler = Depends(get_async_db),
    task_manager: AsyncTaskManager = Depends(get_task_manager),
):
    """Decode multiple transactions asynchronously"""
    if not async_features.is_enabled(AsyncFeature.TRANSACTIONS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        chain = ChainID(evm_chain)

        # Always run as async task since decoding can be slow
        async def _decode_transactions():
            # Would implement actual decoding logic
            # For now, simulate work
            await asyncio.sleep(0.1 * len(tx_hashes))

            return {
                'decoded': len(tx_hashes),
                'failed': 0,
                'results': {},  # Would contain decoded data
            }

        task = await task_manager.spawn_and_track(
            task_name=f'decode_transactions_{chain}',
            coro=_decode_transactions(),
            timeout=300.0,
        )

        return create_success_response({
            'task_id': task.id,
            'status': 'pending',
        })

    except ValueError as e:
        return JSONResponse(
            content=create_error_response(f'Invalid parameters: {e}'),
            status_code=400,
        )
    except Exception as e:
        log.error(f'Error decoding transactions: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']
