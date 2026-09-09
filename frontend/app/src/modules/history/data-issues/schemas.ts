import type { PaginationRequestPayload } from '@/modules/core/common/common-types';
import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';

/**
 * A single auto-remediation attempt. The backend currently records at least the
 * strategy and its outcome; timestamps/attributions may be added later, so the
 * schema stays permissive (extra keys are preserved, rendered when present).
 */
export const AutoRemediationAttempt = z.looseObject({
  attribution: z.string().optional(),
  changedTransactionCount: z.number().optional(),
  customizedTransactionCount: z.number().optional(),
  reason: z.string().optional(),
  result: z.enum([
    'redecoding_failed',
    'redecoding_would_change_balance',
    'redecoding_would_not_change_balance',
  ]).optional(),
  strategy: z.string(),
  success: z.boolean().optional(),
  timestamp: z.number().optional(),
});

export type AutoRemediationAttempt = z.infer<typeof AutoRemediationAttempt>;

/**
 * A persisted data quality issue, as served by `GET /data_issues`. The free-form
 * `payload` differs per kind and is narrowed in transforms (see transforms.ts);
 * here it is kept as a permissive record so backend payload additions don't break
 * deserialization.
 */
export const DataIssue = z.object({
  asset: z.string().nullable(),
  autoRemediationAttempts: z.array(AutoRemediationAttempt).default([]),
  createdAt: z.number(),
  groupIdentifier: z.string().nullable().default(null),
  id: z.number(),
  kind: z.enum(IssueKind),
  location: z.string(),
  locationLabel: z.string().nullable(),
  payload: z.record(z.string(), z.unknown()).default({}),
  protocol: z.string().nullable(),
  resolvedAt: z.number().nullable(),
  severity: z.enum(IssueSeverity),
  state: z.enum(IssueState),
  tsEnd: z.number(),
  tsStart: z.number(),
});

export type DataIssue = z.infer<typeof DataIssue>;

/**
 * `GET /data_issues` collection response. The backend only returns `entriesFound`
 * and `entriesLimit`; we derive `entriesTotal` from `entriesFound` so the shape
 * satisfies the shared `CollectionResponse`/`mapCollectionResponse` contract.
 */
export const DataIssuesCollectionResponse = z
  .object({
    entries: z.array(DataIssue),
    entriesFound: z.number(),
    entriesLimit: z.number().default(-1),
  })
  .transform(response => ({ ...response, entriesTotal: response.entriesFound }));

export type DataIssuesCollectionResponse = z.infer<typeof DataIssuesCollectionResponse>;

/**
 * Request payload for listing data issues.
 *
 * @remarks
 * Field names map 1:1 to the backend query params after snake_case transformation, so
 * `locationLabel` becomes `location_label`. `state` and `kind` are multi-valued.
 */
export interface DataIssuesRequestPayload extends PaginationRequestPayload<DataIssue> {
  readonly state?: string | string[];
  readonly kind?: string | string[];
  readonly location?: string;
  readonly locationLabel?: string;
  readonly asset?: string;
  readonly fromTimestamp?: number;
  readonly toTimestamp?: number;
}

export const NegativeBalancePayload = z.object({
  derivedBalanceBeforeEvent: NumericString,
  eventIdentifier: z.number(),
  inMemoryNegativeAmount: NumericString,
});

export type NegativeBalancePayload = z.infer<typeof NegativeBalancePayload>;

export const RebasingTokenPayload = z.object({
  blockNumber: z.number().nullable(),
  eventIdentifier: z.number(),
  reason: z.enum([
    'archive_node_unavailable',
    'historical_balance_query_failed',
    'missing_transaction',
    'unsupported_bucket',
  ]),
});

export type RebasingTokenPayload = z.infer<typeof RebasingTokenPayload>;

export const CurrentBalanceMismatchPayload = z.object({
  delta: NumericString,
  derivedBalance: NumericString,
  latestEventIdentifier: z.number().nullable(),
  observedBalance: NumericString,
  queriedAtTs: z.number(),
});

export type CurrentBalanceMismatchPayload = z.infer<typeof CurrentBalanceMismatchPayload>;

export const UnmatchedBridgePayload = z.object({
  bridge: z.record(z.string(), z.unknown()).optional(),
  counterparty: z.string().optional(),
  direction: z.enum(['deposit', 'withdrawal']),
  eventIdentifier: z.number(),
  groupIdentifier: z.string(),
});

export type UnmatchedBridgePayload = z.infer<typeof UnmatchedBridgePayload>;
