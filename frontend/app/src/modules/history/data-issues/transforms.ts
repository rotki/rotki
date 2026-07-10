import type { RouteLocationRaw } from 'vue-router';
import type {
  IssueDescription,
  RemediationTimelineItem,
} from '@/modules/history/data-issues/types';
import { fromNullable, getOr } from 'plainfp/option';
import { pipe } from 'plainfp/pipe';
import { IssueKind } from '@/modules/history/data-issues/constants';
import {
  type AutoRemediationAttempt,
  CurrentBalanceMismatchPayload,
  type DataIssue,
  NegativeBalancePayload,
} from '@/modules/history/data-issues/schemas';

/**
 * Turns a raw strategy identifier (e.g. `reprocess_event`) into a human label
 * (`Reprocess event`).
 */
export function humanizeStrategy(strategy: string): string {
  const normalized = strategy.replaceAll(/[_-]+/g, ' ').trim();
  if (normalized.length === 0)
    return strategy;
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

/**
 * Describes what is wrong with an issue, narrowed by its `kind`. Returns the i18n
 * keypath and its interpolation values (the asset as an identifier, the numbers as
 * `BigNumber`s) so the display can render the asset as a resolved symbol and the
 * amounts with the user's decimals setting, rather than baking raw values into a
 * string. Also exposes an optional `eventIdentifier` to deep-link the offending event.
 */
export function describeIssue(issue: DataIssue): IssueDescription {
  if (issue.kind === IssueKind.NEGATIVE_BALANCE) {
    const parsed = NegativeBalancePayload.safeParse(issue.payload);
    if (parsed.success) {
      const payload = parsed.data;
      return {
        amounts: {
          // Signed value: the i18n string no longer prepends a literal "-", so
          // ValueDisplay renders the sign (avoids awkward output like "-< 0.001").
          amount: payload.inMemoryNegativeAmount,
          before: payload.derivedBalanceBeforeEvent,
        },
        asset: issue.asset ?? undefined,
        eventIdentifier: payload.eventIdentifier,
        messageKey: 'data_issues.description.negative_balance',
      };
    }
  }
  else if (issue.kind === IssueKind.CURRENT_BALANCE_MISMATCH) {
    const parsed = CurrentBalanceMismatchPayload.safeParse(issue.payload);
    if (parsed.success) {
      const payload = parsed.data;
      return {
        amounts: {
          delta: payload.delta,
          derived: payload.derivedBalance,
          observed: payload.observedBalance,
        },
        asset: issue.asset ?? undefined,
        eventIdentifier: pipe(
          fromNullable(payload.latestEventIdentifier),
          (option): number | undefined => getOr(option, undefined),
        ),
        messageKey: 'data_issues.description.current_balance_mismatch',
      };
    }
  }

  return { amounts: {}, messageKey: 'data_issues.description.unknown' };
}

/**
 * Deep-link to the offending history event for an issue, or `undefined` when the
 * issue carries no event identifier. For a negative-balance issue the events view
 * needs both `highlightedNegativeBalanceEvent` (the event) and
 * `targetGroupIdentifier` (its group) to page to and highlight the row, so we pass
 * both when the backend supplied the group identifier. When the issue carries an
 * asset we also add it to the query so the events view filters to that asset on
 * arrival (the `asset` matcher key is read straight from the route). Shared by the
 * detail drawer and the inbox panel so both navigate consistently.
 */
export function relatedEventRoute(
  kind: IssueKind,
  eventIdentifier: number | undefined,
  groupIdentifier?: string | null,
  asset?: string | null,
): RouteLocationRaw | undefined {
  if (eventIdentifier === undefined)
    return undefined;

  const name = '/history/events/';
  const query: Record<string, string> = {};

  if (kind === IssueKind.NEGATIVE_BALANCE) {
    query.highlightedNegativeBalanceEvent = eventIdentifier.toString();
    if (groupIdentifier)
      query.targetGroupIdentifier = groupIdentifier;
  }

  if (asset)
    query.asset = asset;

  return Object.keys(query).length > 0 ? { name, query } : { name };
}

function toTimelineItem(attempt: AutoRemediationAttempt): RemediationTimelineItem {
  return {
    attribution: attempt.attribution,
    strategy: attempt.strategy,
    success: attempt.success,
    timestamp: attempt.timestamp,
  };
}

/**
 * Maps the raw auto-remediation attempts into ordered timeline items. Attempts
 * that carry a timestamp are shown oldest-first; the order of timestamp-less
 * attempts (older backend rows) is preserved.
 */
export function toTimelineItems(issue: DataIssue): RemediationTimelineItem[] {
  return issue.autoRemediationAttempts.map(toTimelineItem).sort((a, b) => {
    const left = pipe(fromNullable(a.timestamp), option => getOr(option, 0));
    const right = pipe(fromNullable(b.timestamp), option => getOr(option, 0));
    return left - right;
  });
}
