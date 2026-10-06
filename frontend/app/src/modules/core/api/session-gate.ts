import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { logger } from '@/modules/core/common/logging/logging';
import { liveSessionSignal } from '@/modules/core/session/session-lifecycle';

/** Carried by every request that belongs to the live session, so ending it cancels them as a group. */
export const SESSION_BOUND_TAG = 'session-bound';

/**
 * The live session's signal for a session-bound request, or nothing for a sessionless one.
 *
 * @param url - the request's path, named in the log when it is refused
 * @param sessionless - the request's own `sessionless` option
 * @returns the signal that aborts when the request's session ends
 * @throws RequestCancelledError when the request needs a session and none is live
 */
export function sessionSignalFor(url: string, sessionless: boolean | undefined): AbortSignal | undefined {
  if (sessionless)
    return undefined;

  const signal = liveSessionSignal();
  if (!signal) {
    logger.debug(`refused ${url}: no live session`);
    throw new RequestCancelledError('No live session');
  }
  return signal;
}

/** Joins the session's signal to the request's own; either aborts the request. */
export function withSessionSignal(session: AbortSignal | undefined, request: AbortSignal | null | undefined): AbortSignal | undefined {
  if (!session)
    return request ?? undefined;
  return request ? AbortSignal.any([session, request]) : session;
}
