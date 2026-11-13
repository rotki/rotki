import asyncio
from typing import Any, Literal

from mcp import types
from mcp.server.fastmcp import Context  # noqa: TC002  # FastMCP injects it by its annotation
from pydantic import BaseModel, Field

from rotkehlchen.mcp import accounting
from rotkehlchen.mcp.registry import register_tool
from rotkehlchen.utils.misc import ts_now


class RemediationApproval(BaseModel):
    approve: bool = Field(description='Apply this repair to my rotki history')


@register_tool(name='get_accounting_health')
async def get_accounting_health() -> dict[str, Any]:
    """Start here: whether rotki's derived historical balances can be trusted, and why not.

    ``status`` is the first that applies: ``disabled``, ``unprocessed``,
    ``processing_pending`` (events changed since the last pass), ``blocked`` (a balance bucket
    stopped processing), ``mismatch`` (a derived balance disagrees with the chain),
    ``unverified`` (buckets not compared, or transactions not decoded yet) or ``healthy``.
    Unverified is not healthy: only ``reconciled`` buckets were checked against the chain.

    Also returns the relevant settings, processing freshness, comparison coverage with reason
    codes per status, the stopped buckets (each with a ``bucket_ref`` for ``trace_bucket``),
    pending decoding and issue counts. Read-only: nothing is refreshed or reprocessed.
    """
    return await asyncio.to_thread(accounting.get_accounting_health)


@register_tool(name='list_data_issues')
async def list_data_issues(
        kinds: list[str] | None = None,
        states: list[str] | None = None,
        asset: str | None = None,
        location: str | None = None,
        account: str | None = None,
        limit: int = 50,
        offset: int = 0,
) -> dict[str, Any]:
    """List the data issues of rotki's accounting inbox, with issues of one transaction grouped.

    - ``kinds``: any of ``negative_balance``, ``current_balance_mismatch``,
      ``rebasing_token``, ``unmatched_bridge``. All by default.
    - ``states``: any of ``open``, ``auto_remediating``, ``unresolved``, ``resolved``,
      ``dismissed``. Defaults to the actionable ones (open, auto_remediating, unresolved).
    - ``account``: an account reference (``anon_…``) from another tool.

    ``groups`` lists transactions with several issues. That they share a cause is a
    hypothesis to check with ``inspect_transaction``, not an established fact. Call
    ``explain_data_issue`` with an issue ``id`` for its evidence.
    """
    return await asyncio.to_thread(
        accounting.list_data_issues,
        kinds=kinds,
        states=states,
        asset=asset,
        location=location,
        account=account,
        limit=limit,
        offset=offset,
    )


@register_tool(name='explain_data_issue')
async def explain_data_issue(issue_id: int) -> dict[str, Any]:
    """Explain one data issue from the backend's evidence.

    Returns, kept apart on purpose:

    - ``facts``: what the evidence establishes, with exact decimal amounts (the balance before
      the event, the shortfall, whether the bucket is stopped at this very event).
    - ``hypotheses``: possible causes, each with its ``basis``. Never present one as fact.
    - ``confirmed_conflicts``: contradictions between the issue and the bucket's real state,
      e.g. a dismissed issue whose bucket is still stopped. Dismissing is not repairing.
    - ``trigger_event`` with the rule that decided its balance effects,
      ``same_transaction_effects_on_bucket``, ``affected_later_history`` (events the stop
      kept from being applied), ``missing_prerequisites`` and ``next_actions``.
    """
    return await asyncio.to_thread(accounting.explain_data_issue, issue_id=issue_id)


@register_tool(name='trace_bucket')
async def trace_bucket(
        bucket_ref: str,
        from_timestamp: int | None = None,
        limit: int = 200,
        offset: int | None = None,
) -> dict[str, Any]:
    """Replay every event's effect on one balance bucket, in processing order.

    A bucket is one (location, account, protocol, asset) balance. ``bucket_ref`` comes from
    any other accounting tool. Each row has the exact ``signed_amount``, ``balance_before`` and
    ``balance_after`` as decimal strings, the ``rule`` that produced the effect, the
    ``stored_balance`` of the last processing pass (a differing one means stale metrics) and a
    ``status``: ``applied``, ``stop`` (the balance went negative and processing of the bucket
    stopped), ``negative_awaiting_rebase_reconciliation`` or ``skipped_after_stop``.

    Do not recompute balances yourself: the arithmetic here is exact decimal, while SQL over
    ``amount_float`` is binary floating point. ``timestamp_ms`` is in milliseconds, and so is
    ``from_timestamp``. Without ``offset`` the page starts just before the stop.
    """
    return await asyncio.to_thread(
        accounting.trace_bucket,
        bucket_ref=bucket_ref,
        from_timestamp=from_timestamp,
        limit=limit,
        offset=offset,
    )


@register_tool(name='inspect_transaction')
async def inspect_transaction(group_identifier: str) -> dict[str, Any]:
    """Inspect all events of one transaction and compare them with its saved receipt.

    ``group_identifier`` is a reference from another tool, or a ``group_identifier_hash`` from
    the analytics tables. Returns every event with its customization state, balance effects
    and the rule behind them, the net effect per bucket, and for EVM transactions a
    ``receipt_comparison``: the net per account and asset that the receipt's transfers show
    against what the decoded events record. A discrepancy is evidence, not a verdict:
    wrapping, rebasing, fee-on-transfer and spam tokens differ legitimately. Read-only: the
    saved receipt is used, nothing is queried.
    """
    return await asyncio.to_thread(
        accounting.inspect_transaction,
        group_identifier=group_identifier,
    )


@register_tool(name='explain_bridge_match')
async def explain_bridge_match(event_identifier: int) -> dict[str, Any]:
    """Explain why a bridge leg is or isn't matched with its counterpart on the other chain.

    Lists every candidate the matcher considers, with its ``rejection`` reason
    (``amount_mismatch``, ``same_location``, ``bridge_data_conflict``,
    ``counterparty_mismatch``, ``not_a_counterpart_event``, ``already_linked_or_ignored``,
    ``outside_time_window`` …), the searched window, the leg's ``missing_metadata`` and a
    ``conclusion``. ``zero_eligible_candidates`` does not prove no counterpart exists: it may
    be on an untracked account, not pulled or decoded yet, or outside the searched range.
    """
    return await asyncio.to_thread(
        accounting.explain_bridge_match,
        event_identifier=event_identifier,
    )


@register_tool(name='preview_remediation')
async def preview_remediation(
        kind: Literal['redecode', 'bridge_link'],
        group_identifiers: list[str] | None = None,
        replace_customized: bool = False,
        bridge_event_identifier: int | None = None,
        matched_event_identifier: int | None = None,
) -> dict[str, Any]:
    """Preview a bounded repair and save it as a plan. Nothing in the history changes.

    - ``redecode``: re-decode ``group_identifiers`` (up to 20 transactions) with the current
      decoders. Works on ordinary events too, e.g. old events missing metadata today's
      decoders emit. A transaction with customized events is only replaced when
      ``replace_customized`` is true; otherwise it is shown as ``blocked_by_customization``.
    - ``bridge_link``: link ``bridge_event_identifier`` with ``matched_event_identifier``. The
      candidate must be one ``explain_bridge_match`` reports as eligible.

    Returns the plan: per item the event-level diff, the exact ``bucket_effect_diff``, the
    affected buckets with their current stops and open issues, the remaining uncertainty and
    when the plan expires. Show the user what it changes, then call ``apply_remediation``.
    """
    return await asyncio.to_thread(
        accounting.preview_remediation,
        kind=kind,
        group_identifiers=group_identifiers,
        replace_customized=replace_customized,
        bridge_event_identifier=bridge_event_identifier,
        matched_event_identifier=matched_event_identifier,
    )


@register_tool(name='apply_remediation')
async def apply_remediation(plan_id: str, ctx: Context) -> dict[str, Any]:
    """Ask the user to approve a previewed plan and, if they do, apply and verify it.

    The user approves in their MCP client through an approval prompt that rotki sends; you
    can't approve on their behalf, and a client without approval prompts can't apply plans.
    A declined plan is rejected for good. The backend refuses expired plans and plans whose
    events changed since the preview: preview again in that case.

    After applying, the affected range is reprocessed and the result verified: see
    ``verify_remediation`` for how to read the verdict.
    """
    if not ctx.session.check_client_capability(types.ClientCapabilities(
        elicitation=types.ElicitationCapability(),
    )):
        return accounting.error_result(
            'approval_unavailable',
            'This MCP client cannot show approval prompts, so the plan cannot be applied '
            "from here. A transaction can instead be redecoded from rotki's history view",
        )

    plan = await asyncio.to_thread(accounting.get_remediation_plan, plan_id=plan_id)
    if 'error' in plan:
        return plan
    if (state := plan['result']['state']) != 'pending':
        return accounting.error_result('plan_not_pending', f'The plan is {state}')

    answer = await ctx.elicit(
        message=accounting.describe_plan_for_approval(plan['result']),
        schema=RemediationApproval,
    )
    if answer.action != 'accept' or answer.data.approve is not True:
        await asyncio.to_thread(
            accounting.reject_remediation_plan,
            plan_id=plan_id,
            reason=f'user_{answer.action}' if answer.action != 'accept' else 'user_declined',
        )
        return accounting.error_result('approval_declined', 'The user did not approve the plan')

    return await asyncio.to_thread(
        accounting.apply_remediation_plan,
        plan_id=plan_id,
        approved_at=ts_now(),
    )


@register_tool(name='verify_remediation')
async def verify_remediation(plan_id: str) -> dict[str, Any]:
    """Check whether an applied plan actually repaired what it targeted.

    ``verification.verdict`` is ``repaired``, ``partially_repaired``, ``not_repaired``,
    ``new_problems_revealed`` (a stop moved to a later event or a new one appeared),
    ``not_reevaluated`` (no processing pass has covered the change yet: call again later) or
    ``not_applied``. It is read from the buckets' processing stops, never from issue states
    or job completion: a resolved or dismissed issue does not mean repaired data.
    """
    return await asyncio.to_thread(accounting.verify_remediation_plan, plan_id=plan_id)


@register_tool(name='get_remediation_task')
async def get_remediation_task(task_id: int) -> dict[str, Any]:
    """Check on a ``preview_remediation`` or ``apply_remediation`` that was still running.

    Those tools return a ``still_running`` error with a ``task_id`` when the backend needs
    longer than they wait. Call this with it: while the task runs the same error comes back,
    and once it finished you get the result the original tool would have returned. Only tasks
    these tools started can be checked.
    """
    return await asyncio.to_thread(accounting.get_remediation_task, task_id=task_id)


@register_tool(name='cancel_remediation_task')
async def cancel_remediation_task(task_id: int) -> dict[str, Any]:
    """Cancel a ``preview_remediation`` or ``apply_remediation`` that is still running.

    Cancelling an apply stops it between transactions. Transactions already redecoded stay
    redecoded, and the plan is marked ``partially_applied`` (or ``cancelled`` when nothing was
    applied); ``verify_remediation`` still judges what was applied once rotki reprocesses it.
    Only tasks these tools started can be cancelled.
    """
    return await asyncio.to_thread(accounting.cancel_remediation_task, task_id=task_id)
