import type { IssueDescription, RemediationTimelineItem } from '@/modules/history/data-issues/types';
import { fromNullable, getOr } from 'plainfp/option';
import { pipe } from 'plainfp/pipe';
import { IssueKind } from '@/modules/history/data-issues/constants';
import { type AutoRemediationAttempt, CurrentBalanceMismatchPayload, type DataIssue, NegativeBalancePayload } from '@/modules/history/data-issues/schemas';

export type Translator = (key: string, params?: Record<string, unknown>) => string;

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
 * Builds a human-readable "what's wrong" description from an issue's payload,
 * narrowed by its `kind`. Returns an optional `eventIdentifier` to deep-link to
 * the offending history event when the payload carries one.
 */
export function describeIssue(issue: DataIssue, t: Translator): IssueDescription {
  if (issue.kind === IssueKind.NEGATIVE_BALANCE) {
    const parsed = NegativeBalancePayload.safeParse(issue.payload);
    if (parsed.success) {
      const payload = parsed.data;
      return {
        eventIdentifier: payload.eventIdentifier,
        summary: t('data_issues.description.negative_balance', {
          amount: payload.inMemoryNegativeAmount.abs().toString(),
          asset: issue.asset ?? '',
          before: payload.derivedBalanceBeforeEvent.toString(),
        }),
      };
    }
  }
  else if (issue.kind === IssueKind.CURRENT_BALANCE_MISMATCH) {
    const parsed = CurrentBalanceMismatchPayload.safeParse(issue.payload);
    if (parsed.success) {
      const payload = parsed.data;
      return {
        eventIdentifier: pipe(
          fromNullable(payload.latestEventIdentifier),
          (option): number | undefined => getOr(option, undefined),
        ),
        summary: t('data_issues.description.current_balance_mismatch', {
          asset: issue.asset ?? '',
          delta: payload.delta.toString(),
          derived: payload.derivedBalance.toString(),
          observed: payload.observedBalance.toString(),
        }),
      };
    }
  }

  return { summary: t('data_issues.description.unknown') };
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
  return issue.autoRemediationAttempts
    .map(toTimelineItem)
    .sort((a, b) => {
      const left = pipe(fromNullable(a.timestamp), option => getOr(option, 0));
      const right = pipe(fromNullable(b.timestamp), option => getOr(option, 0));
      return left - right;
    });
}
