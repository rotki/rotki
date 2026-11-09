import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { assert, describe, expect, it } from 'vitest';
import { useBucketReconciliationApi } from '@/modules/history/reconciliation/api/use-bucket-reconciliation-api';

const backendUrl = process.env.VITE_BACKEND_URL;
const ENDPOINT = `${backendUrl}/api/1/balances/historical/reconciliation`;

const COUNTS = { blocked: 0, mismatch: 1, not_compared: 0, pending: 0, reconciled: 2 };

function accountSummary(extra: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    counts: COUNTS,
    history_synced_to: 1_700_000_000,
    is_exchange: false,
    last_compared_at: 1_700_000_100,
    last_event_ts: 1_700_000_000_000,
    location: 'ethereum',
    location_label: '0xA',
    ...extra,
  };
}

function summaryBody(accounts: Record<string, unknown>[] = [accountSummary()]): Record<string, unknown> {
  return {
    result: {
      accounts,
      buckets_total: 3,
      processing: false,
      stale: false,
      totals: COUNTS,
    },
  };
}

describe('useBucketReconciliationApi', () => {
  it('should parse the account summary and keep a null observation null', async () => {
    server.use(http.get(ENDPOINT, () => HttpResponse.json(summaryBody([
      accountSummary({
        buckets: [{
          asset: 'ETH',
          check: null,
          derived_balance: null,
          issue_id: null,
          last_event_ts: null,
          observed_at: null,
          observed_balance: null,
          protocol: null,
          reasons: [],
          status: 'pending',
          stop: null,
        }],
        pagination: { limit: 50, offset: 0, total: 1 },
      }),
    ]))));

    const response = await useBucketReconciliationApi().fetchSummary();

    expect(response.accounts[0].locationLabel).toBe('0xA');
    expect(response.totals.mismatch).toBe(1);
    expect(response.accounts[0].historySyncedTo).toBe(1_700_000_000);
    expect(response.accounts[0].buckets?.[0].observedBalance).toBeNull();
    expect(response.accounts[0].buckets?.[0].derivedBalance).toBeNull();
  });

  it('should scope an account request with its location, label, statuses and page', async () => {
    let sent: URLSearchParams | undefined;
    server.use(http.get(ENDPOINT, ({ request }) => {
      sent = new URL(request.url).searchParams;
      return HttpResponse.json(summaryBody());
    }));

    const account = await useBucketReconciliationApi().fetchAccount({
      limit: 50,
      location: 'ethereum',
      locationLabel: '0xA',
      offset: 10,
      status: ['blocked', 'mismatch'],
    });

    expect(sent?.get('location')).toBe('ethereum');
    expect(sent?.get('location_label')).toBe('0xA');
    expect(sent?.get('status')).toBe('blocked,mismatch');
    expect(sent?.get('limit')).toBe('50');
    expect(sent?.get('offset')).toBe('10');
    assert(account);
    expect(account.isExchange).toBe(false);
  });

  it('should scope a null-label account with an empty location_label and match the null response', async () => {
    let sent: URLSearchParams | undefined;
    server.use(http.get(ENDPOINT, ({ request }) => {
      sent = new URL(request.url).searchParams;
      return HttpResponse.json(summaryBody([
        accountSummary({ location: 'aave', location_label: null }),
      ]));
    }));

    const account = await useBucketReconciliationApi().fetchAccount({
      location: 'aave',
      locationLabel: '',
    });

    expect(sent?.get('location')).toBe('aave');
    expect(sent?.has('location_label')).toBe(true);
    expect(sent?.get('location_label')).toBe('');
    assert(account);
    expect(account.locationLabel).toBeNull();
  });
});
