import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { assert, describe, expect, it } from 'vitest';
import { useDataIssuesApi } from '@/modules/history/data-issues/api/use-data-issues-api';

const backendUrl = process.env.VITE_BACKEND_URL;
const LIST_URL = `${backendUrl}/api/1/data_issues`;
const DISMISS_URL = `${backendUrl}/api/1/data_issues/1/dismiss`;

function listPayload(): { limit: number; offset: number } {
  return { limit: 10, offset: 0 };
}

describe('useDataIssuesApi error classification', () => {
  it('should classify a 404 as not-found', async () => {
    server.use(http.get(LIST_URL, () => HttpResponse.json({ message: 'gone', result: null }, { status: 404 })));

    const result = await useDataIssuesApi().listIssues(listPayload());

    assert(!result.ok);
    expect(result.error.type).toBe('not-found');
  });

  it('should classify a 400 as validation', async () => {
    server.use(http.get(LIST_URL, () => HttpResponse.json({ message: 'bad request', result: null }, { status: 400 })));

    const result = await useDataIssuesApi().listIssues(listPayload());

    assert(!result.ok);
    expect(result.error.type).toBe('validation');
  });

  it('should classify a 409 invalid transition as conflict', async () => {
    server.use(http.get(LIST_URL, () => HttpResponse.json({ message: 'invalid transition', result: null }, { status: 409 })));

    const result = await useDataIssuesApi().listIssues(listPayload());

    assert(!result.ok);
    expect(result.error.type).toBe('conflict');
  });

  it('should carry the backend message through to the error', async () => {
    server.use(http.get(LIST_URL, () => HttpResponse.json({ message: 'gone', result: null }, { status: 404 })));

    const result = await useDataIssuesApi().listIssues(listPayload());

    assert(!result.ok);
    expect(result.error.message).toContain('gone');
  });

  it('should classify a 409 invalid transition on a write action as conflict', async () => {
    server.use(http.patch(DISMISS_URL, () => HttpResponse.json({ message: 'already resolved', result: null }, { status: 409 })));

    const result = await useDataIssuesApi().dismissIssue(1);

    assert(!result.ok);
    expect(result.error.type).toBe('conflict');
  });

  it('should classify a 500 server error as network', async () => {
    server.use(http.get(LIST_URL, () => HttpResponse.json({ message: 'boom', result: null }, { status: 500 })));

    const result = await useDataIssuesApi().listIssues(listPayload());

    assert(!result.ok);
    expect(result.error.type).toBe('network');
  });
});
