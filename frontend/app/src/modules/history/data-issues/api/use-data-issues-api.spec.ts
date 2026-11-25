import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { assert, describe, expect, it } from 'vitest';
import { useDataIssuesApi } from '@/modules/history/data-issues/api/use-data-issues-api';

const backendUrl = process.env.VITE_BACKEND_URL;
const LIST_URL = `${backendUrl}/api/1/data_issues`;
const DISMISS_URL = `${backendUrl}/api/1/data_issues/1/dismiss`;
const REOPEN_URL = `${backendUrl}/api/1/data_issues/1/reopen`;
const RESOLVE_URL = `${backendUrl}/api/1/data_issues/1/resolve_manually`;

function wireIssue(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    asset: 'ETH',
    auto_remediation_attempts: [],
    created_at: 1,
    event_identifier: 5,
    group_identifier: 'g-1',
    id: 1,
    kind: 'missing_cost_basis',
    location: 'ethereum',
    location_label: null,
    payload: {},
    protocol: null,
    resolved_at: null,
    severity: 'warning',
    state: 'open',
    suggested_actions: [],
    ts_end: 1000,
    ts_start: 1000,
    ...overrides,
  };
}

function listPayload(): { limit: number; offset: number } {
  return { limit: 10, offset: 0 };
}

describe('useDataIssuesApi request shape', () => {
  it('should send no ordering params, which the endpoint orders server-side and rejects', async () => {
    let sent: URLSearchParams | undefined;
    server.use(http.get(LIST_URL, ({ request }) => {
      sent = new URL(request.url).searchParams;
      return HttpResponse.json({ message: '', result: { entries: [], entriesFound: 0, entriesLimit: -1, entriesTotal: 0 } });
    }));

    await useDataIssuesApi().listIssues({ ascending: [false], limit: 10, offset: 0, orderByAttributes: ['ts_start'] });

    expect(sent?.has('order_by_attributes')).toBe(false);
    expect(sent?.has('ascending')).toBe(false);
  });

  it('should forward manual_only query parameter when filtering confirmed issues', async () => {
    let sent: URLSearchParams | undefined;
    server.use(http.get(LIST_URL, ({ request }) => {
      sent = new URL(request.url).searchParams;
      return HttpResponse.json({ message: '', result: { entries: [], entriesFound: 0, entriesLimit: -1 } });
    }));

    await useDataIssuesApi().listIssues({ limit: 10, manualOnly: true, offset: 0 });

    expect(sent?.get('manual_only')).toBe('true');
  });

  it('should send disposition and note when resolving manually', async () => {
    let receivedBody: unknown;
    server.use(http.patch(RESOLVE_URL, async ({ request }) => {
      receivedBody = await request.json();
      return HttpResponse.json({ message: '', result: wireIssue({ state: 'resolved' }) });
    }));

    const result = await useDataIssuesApi().resolveIssueManually(1, 'airdrop', 'confirm_zero_basis');

    assert(result.ok);
    expect(receivedBody).toEqual({ disposition: 'confirm_zero_basis', note: 'airdrop' });
  });

  it('should PATCH /reopen and parse the reopened issue', async () => {
    server.use(http.patch(REOPEN_URL, () => HttpResponse.json({ message: '', result: wireIssue({ state: 'open' }) })));

    const result = await useDataIssuesApi().reopenIssue(1);

    assert(result.ok);
    expect(result.value.state).toBe('open');
  });
});

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
