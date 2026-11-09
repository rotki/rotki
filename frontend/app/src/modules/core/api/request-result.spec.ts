import { FetchError } from 'ofetch';
import { assert, describe, expect, it } from 'vitest';
import { FailureCause } from '@/modules/core/api/failure-cause';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { failureCauseOf, fromRequest, isRequestFailure, isRetryableFailure, isUnreachable, RequestCancelled, RequestFailed, toRequestError } from '@/modules/core/api/request-result';
import { createStatusError } from '@/modules/core/api/response-handlers';
import { ApiRequestError } from '@/modules/core/api/types/errors';
import { TaskFailed } from '@/modules/core/tasks/task-result';

describe('failureCauseOf', () => {
  const rejected = new ApiRequestError('key rejected', { failureCause: 'auth', status: 502 });

  it('should read a thrown error\'s cause', () => {
    expect(failureCauseOf(rejected)).toBe('auth');
  });

  it('should read the response body of a status the request did not allow', () => {
    expect(failureCauseOf(createStatusError(403, 'nope', { cause: 'forbidden', message: 'nope' }))).toBe('forbidden');
  });

  it('should read a request failure', () => {
    expect(failureCauseOf(toRequestError(rejected))).toBe('auth');
  });

  it('should read a task failure by its own cause, keeping the thrown value beside it', () => {
    const thrown = new Error('boom');
    const failure = TaskFailed({ cause: thrown, failureCause: FailureCause.LOCAL_DB, message: 'boom' });

    expect(failureCauseOf(failure)).toBe('local_db');
    expect(failure.cause).toBe(thrown);
  });

  it('should reach the thrown value a task failure or domain error wraps', () => {
    expect(failureCauseOf(TaskFailed({ cause: rejected, message: 'key rejected' }))).toBe('auth');
    expect(failureCauseOf({ cause: rejected, message: 'key rejected', type: 'network' })).toBe('auth');
  });

  it.each([
    ['a worded failure', 'something went wrong'],
    ['a plain error', new Error('boom')],
    ['a status error without a body', createStatusError(502)],
    ['nothing', undefined],
  ])('should read %s as unknown', (_name, failure) => {
    expect(failureCauseOf(failure)).toBe('unknown');
  });
});

describe('isRetryableFailure', () => {
  it('should offer no retry for a failure the backend calls permanent', () => {
    expect(isRetryableFailure(new ApiRequestError('key rejected', { failureCause: 'auth' }))).toBe(false);
  });

  it('should offer a retry for a transient failure or one that names no cause', () => {
    expect(isRetryableFailure(new ApiRequestError('down', { failureCause: 'network' }))).toBe(true);
    expect(isRetryableFailure('something went wrong')).toBe(true);
  });
});

describe('toRequestError', () => {
  it('should carry the status and cause of a failure on an allowed status', () => {
    const failure = toRequestError(new ApiRequestError('taken', { failureCause: 'conflict', status: 409 }));

    assert(isRequestFailure(failure));
    expect(failure.status).toBe(409);
    expect(failure.failureCause).toBe('conflict');
  });
});

describe('fromRequest', () => {
  it('should carry the value of a request that resolves', async () => {
    const result = await fromRequest(async () => Promise.resolve({ id: 1 }));

    expect(result).toStrictEqual({ ok: true, value: { id: 1 } });
  });

  it('should carry the status, url and backend message of a failed response', async () => {
    const failure = createStatusError(409, 'generic', { message: 'Report 3 does not exist' });
    failure.request = '/api/1/reports/3';

    const result = await fromRequest(async () => Promise.reject(failure));

    expect(result).toStrictEqual({
      error: RequestFailed({ cause: failure, failureCause: 'unknown', message: 'Report 3 does not exist', path: '/api/1/reports/3', status: 409 }),
      ok: false,
    });
  });

  it('should fall back to the error\'s own message when the response body has none', async () => {
    const failure = createStatusError(502, 'Bad gateway');

    const result = await fromRequest(async () => Promise.reject(failure));

    assert(!result.ok);
    assert(isRequestFailure(result.error));
    expect(result.error.message).toBe('Bad gateway');
    expect(result.error.status).toBe(502);
  });

  it('should leave the status unset for a failure that never got a response', async () => {
    const failure = new TypeError('fetch failed');

    const result = await fromRequest(async () => Promise.reject(failure));

    expect(result).toStrictEqual({
      error: RequestFailed({ cause: failure, failureCause: 'unknown', message: 'fetch failed', path: undefined, status: undefined }),
      ok: false,
    });
  });

  it('should capture a throw before the request starts', async () => {
    const result = await fromRequest(async () => {
      throw new Error('bad payload');
    });

    assert(!result.ok);
    expect(result.error.message).toBe('bad payload');
  });

  it('should mark a request cancelled by the queue as cancelled, not failed', async () => {
    const result = await fromRequest(async () => Promise.reject(new RequestCancelledError('Request was cancelled')));

    expect(result).toStrictEqual({ error: RequestCancelled({ message: 'Request was cancelled' }), ok: false });
    assert(!result.ok);
    expect(isRequestFailure(result.error)).toBe(false);
  });

  it('should mark an aborted request as cancelled, not failed', async () => {
    const result = await fromRequest(async () => Promise.reject(new DOMException('aborted', 'AbortError')));

    assert(!result.ok);
    expect(isRequestFailure(result.error)).toBe(false);
  });

  it('should mark an abort wrapped by the http client as cancelled, not failed', async () => {
    const wrapped = new FetchError('[GET] "/api/1/data_issues": <no response> aborted', { cause: new DOMException('aborted', 'AbortError') });

    const result = await fromRequest(async () => Promise.reject(wrapped));

    assert(!result.ok);
    expect(isRequestFailure(result.error)).toBe(false);
  });

  it('should keep a network failure wrapped by the http client as a failure', async () => {
    const wrapped = new FetchError('[GET] "/api/1/data_issues": <no response> fetch failed', { cause: new TypeError('fetch failed') });

    const result = await fromRequest(async () => Promise.reject(wrapped));

    assert(!result.ok);
    expect(isRequestFailure(result.error)).toBe(true);
  });
});

describe('isUnreachable', () => {
  it('should hold for a request that got no response', () => {
    const noResponse = new FetchError('[GET] "http://127.0.0.1:13024/api/1/banks": <no response> fetch failed');

    expect(isUnreachable(noResponse)).toBe(true);
    expect(isUnreachable(toRequestError(noResponse))).toBe(true);
  });

  it('should not hold for a status the backend answered, as the client rethrows it', () => {
    const answered = createStatusError(500, 'Cache database is locked');

    expect(isUnreachable(answered)).toBe(false);
    expect(isUnreachable(toRequestError(answered))).toBe(false);
  });

  it('should hold for a task that failed because its request got no response', () => {
    const noResponse = new FetchError('[PUT] "http://127.0.0.1:4141/api/1/assets/user": <no response> Failed to fetch');

    expect(isUnreachable(TaskFailed({ cause: noResponse, message: noResponse.message }))).toBe(true);
    expect(isUnreachable(TaskFailed({ message: 'Timed out' }))).toBe(false);
  });

  it('should not hold for an error that is not a fetch failure', () => {
    expect(isUnreachable(new Error('boom'))).toBe(false);
  });
});
