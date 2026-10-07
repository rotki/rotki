import type { ConsolaInstance } from 'consola';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';

type LogFn = ConsolaInstance['error'];

/** Marks a wrapped log function; `Symbol.for` so a re-evaluated module still recognises it. */
const DEMOTED = Symbol.for('rotki.logging.demoted-cancellations');

/**
 * Wraps a log function so that a call carrying a cancelled request logs through `fallback` instead.
 *
 * @remarks
 * A cancelled request is expected, not a failure: a logout, a user switch or a superseded fetch
 * cancels whatever is in flight, and every caller that logs its error would otherwise print one
 * per cancelled request. The cancellation is still logged, at the fallback's level.
 *
 * A function this already wrapped is returned as is, so the logging module being evaluated again
 * (a Vite hot update, `vi.resetModules()` in a spec) does not stack another wrapper on the shared
 * logger each time.
 */
export function demoteCancellations(log: LogFn, fallback: LogFn): LogFn {
  if (DEMOTED in log)
    return log;

  return Object.assign(
    (message: unknown, ...args: unknown[]): void => {
      if (isRequestCancellation(message) || args.some(isRequestCancellation))
        fallback(message, ...args);
      else
        log(message, ...args);
    },
    { [DEMOTED]: true, raw: log.raw },
  );
}
