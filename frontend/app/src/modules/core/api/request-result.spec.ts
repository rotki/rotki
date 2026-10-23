import { FetchError } from 'ofetch';
import { assert, describe, expect, it } from 'vitest';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { fromRequest, isRequestFailure, isUnreachable, RequestCancelled, RequestFailed, toRequestError } from '@/modules/core/api/request-result';
import { createStatusError } from '@/modules/core/api/response-handlers';

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
      error: RequestFailed({ cause: failure, message: 'Report 3 does not exist', path: '/api/1/reports/3', status: 409 }),
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
      error: RequestFailed({ cause: failure, message: 'fetch failed', path: undefined, status: undefined }),
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

  it('should not hold for an error that is not a fetch failure', () => {
    expect(isUnreachable(new Error('boom'))).toBe(false);
  });
});
