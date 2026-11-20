import type { BucketTraceRequest } from '@/modules/history/reconciliation/schemas';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { BUCKET_TRACE_PAGE_SIZE, useBucketTraceApi } from '@/modules/history/reconciliation/api/use-bucket-trace-api';

const ENDPOINT = `${process.env.VITE_BACKEND_URL}/api/1/data_issues/diagnostics/bucket_trace`;

const PAYLOAD = {
  result: {
    pagination: { limit: 50, offset: 0, total: 1, truncated: false },
    rows: [{
      balance_after: '10.5',
      balance_before: '0',
      counterparty: null,
      customized: false,
      direction: 'in',
      event_asset: 'ETH',
      event_identifier: 42,
      event_subtype: 'receive',
      event_type: 'receive',
      group_identifier: '0xtx1',
      rebase_yield: null,
      rule: 'receive',
      sequence_index: 0,
      signed_amount: '10.5',
      status: 'applied',
      stored_balance: '10.5',
      timestamp_ms: 1_700_000_000_000,
    }],
    summary: {
      awaiting_rebase_reconciliation: false,
      derived_balances_stale: false,
      effects_total: 1,
      final_balance: '10.5',
      rebasing_asset: false,
      skipped_after_stop: 0,
      stop_row_index: null,
      stored_balance_mismatches: 0,
    },
  },
};

async function captureRequest(req: BucketTraceRequest): Promise<{ body: unknown; response: Awaited<ReturnType<ReturnType<typeof useBucketTraceApi>['fetchBucketTrace']>> }> {
  let body: unknown;
  server.use(http.post(ENDPOINT, async ({ request }) => {
    body = await request.json();
    return HttpResponse.json(PAYLOAD);
  }));
  const response = await useBucketTraceApi().fetchBucketTrace(req);
  return { body, response };
}

describe('useBucketTraceApi', () => {
  it('should omit null or empty optional fields and parse numeric strings in the response', async () => {
    const { body, response } = await captureRequest({
      asset: 'ETH',
      location: 'ethereum',
      locationLabel: null,
      protocol: '',
    });

    expect(body).toEqual({ asset: 'ETH', limit: BUCKET_TRACE_PAGE_SIZE, location: 'ethereum' });
    expect(response.rows[0].balanceAfter.toString()).toBe('10.5');
    expect(response.summary.finalBalance.toString()).toBe('10.5');
  });

  it('should send location_label, protocol, limit, and offset when provided', async () => {
    const { body } = await captureRequest({
      asset: 'USDC',
      limit: 25,
      location: 'ethereum',
      locationLabel: '0xA',
      offset: 50,
      protocol: 'aave-v3',
    });

    expect(body).toEqual({ asset: 'USDC', limit: 25, location: 'ethereum', location_label: '0xA', offset: 50, protocol: 'aave-v3' });
  });
});
