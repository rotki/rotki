import type { BigNumber } from '@rotki/common';

/**
 * Typed error domain for data-issue API calls, so the UI can branch on the failure kind (friendly
 * copy, refetch on conflict) instead of matching error strings.
 *
 * @remarks
 * Maps the backend status codes: `404` to not-found, `409` to conflict (an invalid state
 * transition), `400` to validation, anything else to network.
 */
export type DataIssueError =
  | { readonly type: 'not-found'; readonly message: string }
  | { readonly type: 'conflict'; readonly message: string }
  | { readonly type: 'validation'; readonly message: string }
  | { readonly type: 'network'; readonly message: string };

/** One entry in the auto-remediation timeline shown in the detail drawer. */
export interface RemediationTimelineItem {
  readonly attribution?: string;
  readonly changedTransactionCount?: number;
  readonly customizedTransactionCount?: number;
  readonly result?:
    | 'redecoding_failed'
    | 'redecoding_would_change_balance'
    | 'redecoding_would_not_change_balance';
  readonly strategy: string;
  readonly success?: boolean;
  readonly timestamp?: number;
}

/**
 * A description of what is wrong, derived from an issue payload. The sentence is
 * kept as an i18n keypath plus its interpolation values (rather than a pre-built
 * string) so the display can render the asset as a resolved symbol via `<i18n-t>`
 * instead of embedding the raw asset identifier in the text.
 */
export interface IssueDescription {
  /** i18n keypath for the full "what's wrong" sentence (detail drawer). */
  readonly messageKey: string;
  /** i18n keypath for a condensed one-line variant used in the inbox card. */
  readonly shortMessageKey: string;
  /** Numeric interpolation values, keyed by placeholder name, rendered with the
   * user's decimals setting (and a full-value tooltip) via `ValueDisplay`. */
  readonly amounts: Record<string, BigNumber>;
  /** Asset identifier for the `{asset}` placeholder, resolved to a symbol on render. */
  readonly asset?: string;
  /** Optional history-event identifier to deep-link to the offending event. */
  readonly eventIdentifier?: number;
}
