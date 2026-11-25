import type { HistoricalAssetPriceResponse } from '@rotki/common';
import { match, type Result } from 'plainfp/result';
import { ZodError } from 'zod';
import { failureCauseOf, isUnreachable } from '@/modules/core/api/request-result';
import { isActionable, isCancellation, type TaskError } from '@/modules/core/tasks/task-result';

/**
 * How a request ended: priced (ok), throttled by an oracle (retried after a backoff), answered
 * with days an oracle could not be reached for (unreachable, each retried after its own wait), failed
 * outright (the backend or the network, so its days are skipped this session after a backoff),
 * answered with a response that does not match the schema (a bug on our side), cancelled, or
 * overtaken by a currency switch. Only days the backend reports as having no price are recorded
 * as such; a failure says nothing about the oracles.
 */
export type RequestResult = 'ok' | 'rate-limited' | 'unreachable' | 'failed' | 'invalid' | 'cancelled' | 'stale';

/** Whether a task failed because the backend's answer did not match the response schema. */
function isInvalidResponse(error: TaskError): boolean {
  return isActionable(error) && error.cause instanceof ZodError;
}

/**
 * How a request that was not overtaken by a currency switch ended. A request that failed on the
 * network or was rate limited ends like an answer saying so, so its days are asked for again.
 */
export function classifyOutcome(outcome: Result<HistoricalAssetPriceResponse, TaskError>): Exclude<RequestResult, 'stale'> {
  return match(outcome, {
    err: (error) => {
      if (isCancellation(error))
        return 'cancelled';
      if (isInvalidResponse(error))
        return 'invalid';
      // a failed task's cause may sit on the error the task layer wraps (a 502 outcome)
      const cause = failureCauseOf(error);
      if (cause === 'rate_limited')
        return 'rate-limited';
      // a request that got no response at all never reached the backend to name a cause
      return cause === 'network' || isUnreachable(error) ? 'unreachable' : 'failed';
    },
    ok: (response) => {
      if (response.rateLimitedPricesTimestamps.length > 0)
        return 'rate-limited';
      return response.failedPricesTimestamps.length > 0 ? 'unreachable' : 'ok';
    },
  });
}
