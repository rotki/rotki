"""Async implementation of statistics endpoints

This module provides high-performance async statistics operations.
"""
import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.errors.api import APIError
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix="/api/1", tags=["statistics"])


# Pydantic models
class NetValueQuery(BaseModel):
    """Parameters for net value statistics"""
    from_timestamp: Optional[int] = Field(default=None, ge=0)
    to_timestamp: Optional[int] = Field(default=None, ge=0)
    include_locations: Optional[list[str]] = None
    exclude_locations: Optional[list[str]] = None


class AssetBalanceQuery(BaseModel):
    """Parameters for asset balance statistics"""
    asset: str
    from_timestamp: Optional[int] = Field(default=None, ge=0)
    to_timestamp: Optional[int] = Field(default=None, ge=0)
    include_locations: Optional[list[str]] = None
    exclude_locations: Optional[list[str]] = None


class ValueDistributionQuery(BaseModel):
    """Parameters for value distribution statistics"""
    distribution_by: str = Field(default="location", regex="^(location|asset)$")


class StatisticsRenderQuery(BaseModel):
    """Parameters for rendering statistics"""
    from_timestamp: Optional[int] = Field(default=None, ge=0)
    to_timestamp: Optional[int] = Field(default=None, ge=0)
    render_type: str = Field(default="graph", regex="^(graph|table)$")


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError("RestAPI injection not configured")


@router.post("/statistics/netvalue", response_model=dict)
async def get_net_value_statistics(
    query: NetValueQuery,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get net value statistics over time"""
    if not async_features.is_enabled(AsyncFeature.STATISTICS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Parse locations
        include_locations = None
        exclude_locations = None
        
        if query.include_locations:
            include_locations = []
            for loc in query.include_locations:
                try:
                    include_locations.append(Location.deserialize(loc))
                except Exception as e:
                    return JSONResponse(
                        content=create_error_response(f"Invalid location: {loc}"),
                        status_code=400,
                    )
        
        if query.exclude_locations:
            exclude_locations = []
            for loc in query.exclude_locations:
                try:
                    exclude_locations.append(Location.deserialize(loc))
                except Exception as e:
                    return JSONResponse(
                        content=create_error_response(f"Invalid location: {loc}"),
                        status_code=400,
                    )
        
        # Get statistics
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            stats = rest_api.rotkehlchen.data.db.get_netvalue_statistics(
                cursor=cursor,
                from_ts=Timestamp(query.from_timestamp) if query.from_timestamp else Timestamp(0),
                to_ts=Timestamp(query.to_timestamp) if query.to_timestamp else None,
                include_locations=include_locations,
                exclude_locations=exclude_locations,
            )
        
        # Format response
        data = []
        times = []
        for entry in stats:
            times.append(entry.timestamp)
            data.append(str(entry.value))
        
        return create_success_response({
            'times': times,
            'data': data,
        })
        
    except Exception as e:
        log.error(f"Error getting net value statistics: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/statistics/balance", response_model=dict)
async def get_asset_balance_statistics(
    query: AssetBalanceQuery,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get balance statistics for a specific asset over time"""
    if not async_features.is_enabled(AsyncFeature.STATISTICS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Validate asset
        try:
            asset = Asset(query.asset)
        except UnknownAsset:
            return JSONResponse(
                content=create_error_response(f"Unknown asset: {query.asset}"),
                status_code=400,
            )
        
        # Parse locations
        include_locations = None
        exclude_locations = None
        
        if query.include_locations:
            include_locations = []
            for loc in query.include_locations:
                try:
                    include_locations.append(Location.deserialize(loc))
                except Exception as e:
                    return JSONResponse(
                        content=create_error_response(f"Invalid location: {loc}"),
                        status_code=400,
                    )
        
        if query.exclude_locations:
            exclude_locations = []
            for loc in query.exclude_locations:
                try:
                    exclude_locations.append(Location.deserialize(loc))
                except Exception as e:
                    return JSONResponse(
                        content=create_error_response(f"Invalid location: {loc}"),
                        status_code=400,
                    )
        
        # Get statistics
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            stats = rest_api.rotkehlchen.data.db.get_asset_balance_statistics(
                cursor=cursor,
                asset=asset,
                from_ts=Timestamp(query.from_timestamp) if query.from_timestamp else Timestamp(0),
                to_ts=Timestamp(query.to_timestamp) if query.to_timestamp else None,
                include_locations=include_locations,
                exclude_locations=exclude_locations,
            )
        
        # Format response
        data = []
        times = []
        for entry in stats:
            times.append(entry.timestamp)
            data.append({
                'amount': str(entry.amount),
                'usd_value': str(entry.usd_value),
            })
        
        return create_success_response({
            'times': times,
            'data': data,
            'asset': query.asset,
        })
        
    except Exception as e:
        log.error(f"Error getting asset balance statistics: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/statistics/value_distribution", response_model=dict)
async def get_value_distribution(
    query: ValueDistributionQuery,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get current value distribution by location or asset"""
    if not async_features.is_enabled(AsyncFeature.STATISTICS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get current balances
        balances = await asyncio.to_thread(
            rest_api.rotkehlchen.query_balances,
            save_data=False,
            ignore_cache=False,
        )
        
        distribution = {}
        
        if query.distribution_by == "location":
            # Distribute by location
            for location, location_data in balances.items():
                if location == "net_value":
                    continue
                
                total_value = FVal(0)
                for asset_data in location_data.values():
                    if isinstance(asset_data, dict) and 'usd_value' in asset_data:
                        total_value += FVal(asset_data['usd_value'])
                
                if total_value > 0:
                    distribution[str(location)] = str(total_value)
        
        else:  # distribution_by == "asset"
            # Distribute by asset
            asset_totals = {}
            
            for location, location_data in balances.items():
                if location == "net_value":
                    continue
                
                for asset, asset_data in location_data.items():
                    if isinstance(asset_data, dict) and 'usd_value' in asset_data:
                        if asset not in asset_totals:
                            asset_totals[asset] = FVal(0)
                        asset_totals[asset] += FVal(asset_data['usd_value'])
            
            # Sort by value and take top assets
            sorted_assets = sorted(
                asset_totals.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]  # Top 20 assets
            
            for asset, value in sorted_assets:
                if value > 0:
                    distribution[asset] = str(value)
        
        return create_success_response({
            'distribution': distribution,
            'distribution_by': query.distribution_by,
        })
        
    except Exception as e:
        log.error(f"Error getting value distribution: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/statistics/renderer", response_model=dict)
async def render_statistics(
    query: StatisticsRenderQuery,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Render statistics in various formats"""
    if not async_features.is_enabled(AsyncFeature.STATISTICS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get net value statistics
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            stats = rest_api.rotkehlchen.data.db.get_netvalue_statistics(
                cursor=cursor,
                from_ts=Timestamp(query.from_timestamp) if query.from_timestamp else Timestamp(0),
                to_ts=Timestamp(query.to_timestamp) if query.to_timestamp else None,
            )
        
        if query.render_type == "graph":
            # Format for graph rendering
            times = []
            values = []
            for entry in stats:
                times.append(entry.timestamp)
                values.append(float(entry.value))
            
            return create_success_response({
                'type': 'graph',
                'data': {
                    'x': times,
                    'y': values,
                    'name': 'Net Value',
                    'type': 'scatter',
                    'mode': 'lines',
                },
            })
        
        else:  # render_type == "table"
            # Format for table rendering
            rows = []
            for entry in stats:
                rows.append({
                    'timestamp': entry.timestamp,
                    'datetime': Timestamp(entry.timestamp).to_date_display(),
                    'value': str(entry.value),
                })
            
            return create_success_response({
                'type': 'table',
                'columns': ['timestamp', 'datetime', 'value'],
                'data': rows,
            })
        
    except Exception as e:
        log.error(f"Error rendering statistics: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/statistics/wrap", response_model=dict)
async def get_statistics_wrap(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get year-end wrap statistics"""
    if not async_features.is_enabled(AsyncFeature.STATISTICS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get current year
        from datetime import datetime
        current_year = datetime.now().year
        
        # Get statistics for the year
        year_start = Timestamp(int(datetime(current_year, 1, 1).timestamp()))
        year_end = Timestamp(int(datetime(current_year, 12, 31, 23, 59, 59).timestamp()))
        
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            # Get net value at start and end of year
            start_value = rest_api.rotkehlchen.data.db.get_netvalue_at_timestamp(
                cursor=cursor,
                timestamp=year_start,
            )
            end_value = rest_api.rotkehlchen.data.db.get_netvalue_at_timestamp(
                cursor=cursor,
                timestamp=year_end,
            )
            
            # Get transaction count
            tx_count = cursor.execute(
                "SELECT COUNT(*) FROM history_events WHERE timestamp >= ? AND timestamp <= ?",
                (year_start, year_end),
            ).fetchone()[0]
            
            # Get most traded assets
            most_traded = cursor.execute("""
                SELECT asset, COUNT(*) as count 
                FROM history_events 
                WHERE timestamp >= ? AND timestamp <= ? 
                GROUP BY asset 
                ORDER BY count DESC 
                LIMIT 10
            """, (year_start, year_end)).fetchall()
        
        # Calculate growth
        growth = FVal(0)
        growth_percentage = FVal(0)
        if start_value and end_value and start_value > 0:
            growth = end_value - start_value
            growth_percentage = (growth / start_value) * 100
        
        return create_success_response({
            'year': current_year,
            'start_value': str(start_value) if start_value else "0",
            'end_value': str(end_value) if end_value else "0",
            'growth': str(growth),
            'growth_percentage': str(growth_percentage),
            'transaction_count': tx_count,
            'most_traded_assets': [
                {'asset': row[0], 'count': row[1]}
                for row in most_traded
            ],
        })
        
    except Exception as e:
        log.error(f"Error getting statistics wrap: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']