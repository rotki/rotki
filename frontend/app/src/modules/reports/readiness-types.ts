import { snakeCase } from 'es-toolkit';
import { z } from 'zod';

/**
 * Normalizes `openIssuesByKind` keys back to snake_case `IssueKind` values because `rotki-api`
 * recursively camelCases response object keys (for example `missing_price` to `missingPrice`).
 */
const OpenIssuesByKind = z.record(z.string(), z.number()).default({}).transform((record) => {
  const normalized: Record<string, number> = {};
  for (const [key, count] of Object.entries(record))
    normalized[snakeCase(key)] = count;
  return normalized;
});

/**
 * Report readiness summary returned on `POST /api/1/history/events/pnl`.
 *
 * @remarks
 * `ready` is true if and only if `stale` is false and `openIssuesCount` is 0 over all
 * non-terminal data issues with `ts_start <= evaluated_through_ts`. `numUnruledEvents` is
 * informational and never blocks `ready`.
 */
export const ReportReadiness = z.object({
  evaluatedThroughTs: z.number().nullable().default(null),
  numUnpricedEvents: z.number().default(0),
  numUnruledEvents: z.number().default(0),
  openIssuesByKind: OpenIssuesByKind,
  openIssuesCount: z.number().default(0),
  ready: z.boolean(),
  stale: z.boolean(),
});

export type ReportReadiness = z.infer<typeof ReportReadiness>;

export const RealizedPnlReadinessResponse = z.object({
  numUnpricedEvents: z.number().default(0),
  numUnruledEvents: z.number().default(0),
  reportReadiness: ReportReadiness,
  stale: z.boolean(),
});

export type RealizedPnlReadinessResponse = z.infer<typeof RealizedPnlReadinessResponse>;

export interface ReportReadinessQuery {
  readonly fromTimestamp?: number;
  readonly toTimestamp?: number;
}
