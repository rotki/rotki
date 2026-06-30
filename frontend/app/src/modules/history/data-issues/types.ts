/**
 * Typed error domain for data-issue API calls, so the UI can branch on the
 * failure kind (friendly copy, refetch on conflict) instead of matching error
 * strings. Maps to the backend status codes: 404 -> not-found,
 * 409 -> conflict (invalid state transition), 400 -> validation, else network.
 */
export type DataIssueError =
  | { readonly type: 'not-found'; readonly message: string }
  | { readonly type: 'conflict'; readonly message: string }
  | { readonly type: 'validation'; readonly message: string }
  | { readonly type: 'network'; readonly message: string };

export function dataIssueErrorMessage(error: DataIssueError): string {
  return error.message;
}

/** One entry in the auto-remediation timeline shown in the detail drawer. */
export interface RemediationTimelineItem {
  readonly strategy: string;
  readonly success?: boolean;
  readonly timestamp?: number;
  readonly attribution?: string;
}

/** A human-readable description of what is wrong, derived from an issue payload. */
export interface IssueDescription {
  readonly summary: string;
  /** Optional history-event identifier to deep-link to the offending event. */
  readonly eventIdentifier?: number;
}
