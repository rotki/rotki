import type { IssueDescription } from '@/modules/history/data-issues/types';
import { type BigNumber, bigNumberify, Zero } from '@rotki/common';
import { msg } from '@/message-key';
import { IssueKind, IssueState } from '@/modules/history/data-issues/constants';
import {
  type DataIssue,
  IncompleteSwapPayload,
  type IssueResolution,
  IssueResolution as IssueResolutionSchema,
  MissingCostBasisPayload,
  MissingPricePayload,
  NegativeBalancePayload,
  UnmatchedExchangeTransferPayload,
} from '@/modules/history/data-issues/schemas';

export function describeMissingPrice(issue: DataIssue): IssueDescription | undefined {
  const parsed = MissingPricePayload.safeParse(issue.payload);
  if (!parsed.success)
    return undefined;
  const payload = parsed.data;
  return {
    amounts: { amount: payload.amount },
    asset: issue.asset ?? undefined,
    eventIdentifier: payload.eventIdentifier,
    messageKey: msg.$t('data_issues.description.missing_price'),
    shortMessageKey: msg.$t('data_issues.description_short.missing_price'),
    toAsset: payload.toAsset,
  };
}

export function describeMissingCostBasis(issue: DataIssue): IssueDescription | undefined {
  const parsed = MissingCostBasisPayload.safeParse(issue.payload);
  if (!parsed.success)
    return undefined;
  const payload = parsed.data;
  return {
    amounts: {
      covered: payload.coveredAmount,
      requested: payload.requestedAmount,
      uncovered: payload.uncoveredAmount,
    },
    asset: issue.asset ?? undefined,
    eventIdentifier: payload.eventIdentifier,
    messageKey: msg.$t('data_issues.description.missing_cost_basis'),
    shortMessageKey: msg.$t('data_issues.description_short.missing_cost_basis'),
  };
}

export function describeIncompleteSwap(issue: DataIssue): IssueDescription | undefined {
  const parsed = IncompleteSwapPayload.safeParse(issue.payload);
  if (!parsed.success)
    return undefined;
  const payload = parsed.data;
  const firstExcludedAsset = payload.excludedAssets[0];
  const base = {
    amounts: {},
    asset: firstExcludedAsset ?? issue.asset ?? undefined,
    eventIdentifier: payload.eventIdentifier,
  };

  switch (payload.missingOrExcludedReason) {
    case 'ignored_asset':
      return {
        ...base,
        messageKey: msg.$t('data_issues.description.incomplete_swap_ignored_asset'),
        shortMessageKey: msg.$t('data_issues.description_short.incomplete_swap_ignored_asset'),
      };
    case 'ignored_action':
      return {
        ...base,
        messageKey: msg.$t('data_issues.description.incomplete_swap_ignored_action'),
        shortMessageKey: msg.$t('data_issues.description_short.incomplete_swap_ignored_action'),
      };
    case 'missing_counterpart_leg':
      return {
        ...base,
        messageKey: msg.$t('data_issues.description.incomplete_swap_missing_leg'),
        shortMessageKey: msg.$t('data_issues.description_short.incomplete_swap_missing_leg'),
      };
  }
}

export function describeUnmatchedExchangeTransfer(issue: DataIssue): IssueDescription | undefined {
  const parsed = UnmatchedExchangeTransferPayload.safeParse(issue.payload);
  if (!parsed.success)
    return undefined;
  const payload = parsed.data;
  const isSpend = payload.subtype === 'spend';
  return {
    amounts: { amount: payload.amount },
    asset: issue.asset ?? undefined,
    eventIdentifier: payload.eventIdentifier,
    messageKey: isSpend
      ? msg.$t('data_issues.description.unmatched_exchange_transfer_spend')
      : msg.$t('data_issues.description.unmatched_exchange_transfer_receive'),
    shortMessageKey: isSpend
      ? msg.$t('data_issues.description_short.unmatched_exchange_transfer_spend')
      : msg.$t('data_issues.description_short.unmatched_exchange_transfer_receive'),
  };
}

/**
 * Parses `payload.resolution` when present, returning manual confirmation audit metadata.
 */
export function extractIssueResolution(issue: DataIssue): IssueResolution | undefined {
  const raw = issue.payload?.resolution;
  if (!raw || typeof raw !== 'object')
    return undefined;
  const parsed = IssueResolutionSchema.safeParse(raw);
  return parsed.success ? parsed.data : undefined;
}

/** Whether the issue was explicitly confirmed by the user (`state === 'resolved'` and `payload.resolution.manual === true`). */
export function isManuallyConfirmed(issue: DataIssue): boolean {
  return issue.state === IssueState.RESOLVED && extractIssueResolution(issue)?.manual === true;
}

const zeroImpact = (): BigNumber => Zero;

const IMPACT_EXTRACTORS: Record<IssueKind, (issue: DataIssue) => BigNumber> = {
  [IssueKind.CURRENT_BALANCE_MISMATCH]: zeroImpact,
  [IssueKind.INCOMPLETE_SWAP]: (issue) => {
    const parsed = IncompleteSwapPayload.safeParse(issue.payload);
    if (!parsed.success)
      return Zero;
    return parsed.data.presentLegs.reduce((sum, leg) => sum.plus(leg.amount.abs()), bigNumberify(0));
  },
  [IssueKind.INVALID_EVENT_AMOUNT]: zeroImpact,
  [IssueKind.MISSING_COST_BASIS]: (issue) => {
    const parsed = MissingCostBasisPayload.safeParse(issue.payload);
    return parsed.success ? parsed.data.uncoveredAmount.abs() : Zero;
  },
  [IssueKind.MISSING_PRICE]: (issue) => {
    const parsed = MissingPricePayload.safeParse(issue.payload);
    return parsed.success ? parsed.data.amount.abs() : Zero;
  },
  [IssueKind.NEGATIVE_BALANCE]: (issue) => {
    const parsed = NegativeBalancePayload.safeParse(issue.payload);
    return parsed.success ? parsed.data.inMemoryNegativeAmount.abs() : Zero;
  },
  [IssueKind.REBASING_TOKEN]: zeroImpact,
  [IssueKind.UNMATCHED_BRIDGE]: zeroImpact,
  [IssueKind.UNMATCHED_EXCHANGE_TRANSFER]: (issue) => {
    const parsed = UnmatchedExchangeTransferPayload.safeParse(issue.payload);
    return parsed.success ? parsed.data.amount.abs() : Zero;
  },
};

/**
 * Extracts a comparable quantitative impact magnitude from an issue payload so checklists can
 * surface higher-impact items ahead of dust before breaking ties by timestamp.
 */
export function issueImpactMagnitude(issue: DataIssue): BigNumber {
  return IMPACT_EXTRACTORS[issue.kind](issue);
}

/**
 * Sorts issues by impact magnitude descending, then by event timestamp (`tsEnd`) descending, then
 * by id descending for deterministic ordering.
 */
export function sortIssuesByImpact(issues: readonly DataIssue[]): DataIssue[] {
  return [...issues].sort((left, right) => {
    const impactDiff = issueImpactMagnitude(right).comparedTo(issueImpactMagnitude(left));
    if (impactDiff !== null && impactDiff !== 0)
      return impactDiff;
    if (right.tsEnd !== left.tsEnd)
      return right.tsEnd - left.tsEnd;
    return right.id - left.id;
  });
}
