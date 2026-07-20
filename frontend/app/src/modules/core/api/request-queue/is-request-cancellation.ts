import { isAbortError } from '@/modules/core/common/helpers/is-of-enum';
import { RequestCancelledError } from './errors';

/**
 * Check if an error means the request was cancelled rather than failed.
 *
 * Covers both cancellation paths: queued requests rejected by
 * `cancel`/`cancelByTag`/`cancelAllQueued`, and in-flight requests aborted
 * through their `AbortController`. Cancellation is expected during logout,
 * user switch, session sync, quit and table/history navigation, so callers
 * should bail out quietly instead of notifying the user.
 */
export function isRequestCancellation(error: unknown): boolean {
  return error instanceof RequestCancelledError || isAbortError(error);
}
