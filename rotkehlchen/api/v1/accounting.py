"""Async implementation of accounting and reporting endpoints

This module provides high-performance async accounting operations.
"""
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from rotkehlchen.accounting.rules import AccountingRule
from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1', tags=['accounting'])


# Pydantic models
class ReportGeneration(BaseModel):
    """Parameters for generating accounting reports"""
    from_timestamp: int = Field(..., ge=0)
    to_timestamp: int = Field(..., ge=0)
    async_query: bool = Field(default=True)
    profit_currency: str = Field(default='USD')


class AccountingRuleData(BaseModel):
    """Data for creating/editing accounting rules"""
    event_type: str
    event_subtype: str | None = None
    counterparty: str | None = None
    rule: str
    taxable: bool | None = None
    count_entire_amount_spend: bool | None = None
    count_cost_basis_pnl: bool | None = None
    accounting_treatment: str | None = None


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError('RestAPI injection not configured')


@router.get('/reports', response_model=dict)
async def get_reports(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get list of all accounting reports"""
    if not async_features.is_enabled(AsyncFeature.ACCOUNTING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get reports from database
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            reports = rest_api.rotkehlchen.data.db.get_accounting_reports(cursor)

        # Format response
        report_list = [{
                'identifier': report.identifier,
                'start_ts': report.start_ts,
                'end_ts': report.end_ts,
                'timestamp': report.timestamp,
                'profit_currency': report.profit_currency,
                'total_cost_basis': str(report.total_cost_basis),
                'total_taxable_profit_loss': str(report.total_taxable_profit_loss),
                'total_free_profit_loss': str(report.total_free_profit_loss),
                'settings': report.settings,
            } for report in reports]

        return create_success_response({'entries': report_list})

    except Exception as e:
        log.error(f'Error getting reports: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/reports', response_model=dict)
async def generate_report(
    params: ReportGeneration,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Generate a new accounting report"""
    if not async_features.is_enabled(AsyncFeature.ACCOUNTING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate time range
        if params.from_timestamp >= params.to_timestamp:
            return JSONResponse(
                content=create_error_response('from_timestamp must be less than to_timestamp'),
                status_code=400,
            )

        if params.async_query:
            # Spawn async task
            task = rest_api.rotkehlchen.task_manager.spawn_task(
                task_name='generate_accounting_report',
                method=rest_api.rotkehlchen.generate_report,
                from_ts=Timestamp(params.from_timestamp),
                to_ts=Timestamp(params.to_timestamp),
                profit_currency=params.profit_currency,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous generation
        report = await asyncio.to_thread(
            rest_api.rotkehlchen.generate_report,
            from_ts=Timestamp(params.from_timestamp),
            to_ts=Timestamp(params.to_timestamp),
            profit_currency=params.profit_currency,
        )

        return create_success_response({
            'identifier': report.identifier,
            'result': report.serialize(),
        })

    except Exception as e:
        log.error(f'Error generating report: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/reports/{report_id}', response_model=dict)
async def get_report(
    report_id: int,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get a specific accounting report"""
    if not async_features.is_enabled(AsyncFeature.ACCOUNTING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get report from database
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            report = rest_api.rotkehlchen.data.db.get_accounting_report(cursor, report_id)

        if not report:
            return JSONResponse(
                content=create_error_response(f'Report with id {report_id} not found'),
                status_code=404,
            )

        return create_success_response(report.serialize())

    except Exception as e:
        log.error(f'Error getting report: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/reports/{report_id}/data', response_model=dict)
async def get_report_data(
    report_id: int,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get report data (events and trades)"""
    if not async_features.is_enabled(AsyncFeature.ACCOUNTING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get report data
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            report_data = rest_api.rotkehlchen.data.db.get_report_data(cursor, report_id)

        if not report_data:
            return JSONResponse(
                content=create_error_response(f'Report data for id {report_id} not found'),
                status_code=404,
            )

        return create_success_response(report_data)

    except Exception as e:
        log.error(f'Error getting report data: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/reports/{report_id}', response_model=dict)
async def delete_report(
    report_id: int,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Delete an accounting report"""
    if not async_features.is_enabled(AsyncFeature.ACCOUNTING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Delete report
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            success = rest_api.rotkehlchen.data.db.delete_accounting_report(write_cursor, report_id)

        if not success:
            return JSONResponse(
                content=create_error_response(f'Report with id {report_id} not found'),
                status_code=404,
            )

        return create_success_response({'result': True})

    except Exception as e:
        log.error(f'Error deleting report: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/accounting/rules', response_model=dict)
async def get_accounting_rules(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get all accounting rules"""
    if not async_features.is_enabled(AsyncFeature.ACCOUNTING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get rules from database
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            rules = rest_api.rotkehlchen.data.db.get_accounting_rules(cursor)

        # Format response
        rule_list = [rule.serialize() for rule in rules]

        return create_success_response({'entries': rule_list})

    except Exception as e:
        log.error(f'Error getting accounting rules: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/accounting/rules', response_model=dict)
async def add_accounting_rule(
    rule_data: AccountingRuleData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add a new accounting rule"""
    if not async_features.is_enabled(AsyncFeature.ACCOUNTING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Create accounting rule
        rule = AccountingRule(
            event_type=rule_data.event_type,
            event_subtype=rule_data.event_subtype,
            counterparty=rule_data.counterparty,
            rule=rule_data.rule,
            taxable=rule_data.taxable,
            count_entire_amount_spend=rule_data.count_entire_amount_spend,
            count_cost_basis_pnl=rule_data.count_cost_basis_pnl,
            accounting_treatment=rule_data.accounting_treatment,
        )

        # Add to database
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            identifier = rest_api.rotkehlchen.data.db.add_accounting_rule(write_cursor, rule)

        return create_success_response({
            'identifier': identifier,
            'rule': rule.serialize(),
        })

    except Exception as e:
        log.error(f'Error adding accounting rule: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch('/accounting/rules', response_model=dict)
async def edit_accounting_rule(
    rule_data: dict = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Edit an existing accounting rule"""
    if not async_features.is_enabled(AsyncFeature.ACCOUNTING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get rule identifier
        identifier = rule_data.get('identifier')
        if not identifier:
            return JSONResponse(
                content=create_error_response('identifier is required'),
                status_code=400,
            )

        # Update rule in database
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            success = rest_api.rotkehlchen.data.db.edit_accounting_rule(
                write_cursor,
                identifier=identifier,
                rule_data=rule_data,
            )

        if not success:
            return JSONResponse(
                content=create_error_response(f'Rule with identifier {identifier} not found'),
                status_code=404,
            )

        return create_success_response({'result': True})

    except Exception as e:
        log.error(f'Error editing accounting rule: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/accounting/rules', response_model=dict)
async def delete_accounting_rules(
    identifiers: list[int] = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Delete accounting rules"""
    if not async_features.is_enabled(AsyncFeature.ACCOUNTING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Delete rules from database
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            deleted_count = rest_api.rotkehlchen.data.db.delete_accounting_rules(
                write_cursor,
                identifiers=identifiers,
            )

        return create_success_response({
            'result': True,
            'deleted': deleted_count,
        })

    except Exception as e:
        log.error(f'Error deleting accounting rules: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/accounting/rules/import', response_model=dict)
async def import_accounting_rules(
    file: UploadFile = File(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Import accounting rules from file"""
    if not async_features.is_enabled(AsyncFeature.ACCOUNTING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Read file content
        content = await file.read()

        # Import rules
        imported_count = await asyncio.to_thread(
            rest_api.rotkehlchen.import_accounting_rules,
            rules_data=content,
        )

        return create_success_response({
            'result': True,
            'imported': imported_count,
        })

    except Exception as e:
        log.error(f'Error importing accounting rules: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/accounting/rules/export', response_model=Any)
async def export_accounting_rules(
    rest_api: RestAPI = Depends(get_rest_api),
) -> Any:
    """Export accounting rules to file"""
    if not async_features.is_enabled(AsyncFeature.ACCOUNTING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Export rules
        export_path = await asyncio.to_thread(
            rest_api.rotkehlchen.export_accounting_rules,
        )

        return FileResponse(
            path=export_path,
            filename='accounting_rules.json',
            media_type='application/json',
        )

    except Exception as e:
        log.error(f'Error exporting accounting rules: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']
