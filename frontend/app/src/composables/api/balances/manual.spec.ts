import type { ManualBalance, RawManualBalance } from '@/types/manual-balances';
import { bigNumberify } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BalanceType } from '@/types/balances';
import { useManualBalancesApi } from './manual';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/balances/manual', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('queryManualBalances', () => {
    it('fetches manual balances with async_query param', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances/manual`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 123,
            },
            message: '',
          });
        }),
      );

      const { queryManualBalances } = useManualBalancesApi();
      const result = await queryManualBalances();

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(123);
    });

    it('includes value_threshold when provided', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances/manual`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 456,
            },
            message: '',
          });
        }),
      );

      const { queryManualBalances } = useManualBalancesApi();
      await queryManualBalances('1000');

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('value_threshold')).toBe('1000');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/balances/manual`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to query balances',
          })),
      );

      const { queryManualBalances } = useManualBalancesApi();

      await expect(queryManualBalances())
        .rejects
        .toThrow('Failed to query balances');
    });
  });

  describe('addManualBalances', () => {
    it('sends PUT request with snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/balances/manual`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              task_id: 789,
            },
            message: '',
          });
        }),
      );

      const { addManualBalances } = useManualBalancesApi();
      const balances: RawManualBalance[] = [
        {
          amount: bigNumberify('1.5'),
          asset: 'ETH',
          balanceType: BalanceType.ASSET,
          label: 'My Wallet',
          location: 'blockchain',
          tags: ['savings'],
        },
      ];

      const result = await addManualBalances(balances);

      expect(capturedBody).toEqual({
        async_query: true,
        balances: [
          {
            amount: '1.5',
            asset: 'ETH',
            balance_type: 'asset',
            label: 'My Wallet',
            location: 'blockchain',
            tags: ['savings'],
          },
        ],
      });
      expect(result.taskId).toBe(789);
    });

    it('filters out null tags due to nonEmptyProperties', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/balances/manual`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              task_id: 100,
            },
            message: '',
          });
        }),
      );

      const { addManualBalances } = useManualBalancesApi();
      const balances: RawManualBalance[] = [
        {
          amount: bigNumberify('100'),
          asset: 'BTC',
          balanceType: BalanceType.LIABILITY,
          label: 'Loan',
          location: 'external',
          tags: null,
        },
      ];

      await addManualBalances(balances);

      // nonEmptyProperties filters out null values, so tags should not be present
      expect(capturedBody).toEqual({
        async_query: true,
        balances: [
          {
            amount: '100',
            asset: 'BTC',
            balance_type: 'liability',
            label: 'Loan',
            location: 'external',
          },
        ],
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/balances/manual`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid balance data',
          })),
      );

      const { addManualBalances } = useManualBalancesApi();

      await expect(addManualBalances([]))
        .rejects
        .toThrow('Invalid balance data');
    });
  });

  describe('editManualBalances', () => {
    it('sends PATCH request with snake_case payload including identifier', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/balances/manual`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              task_id: 200,
            },
            message: '',
          });
        }),
      );

      const { editManualBalances } = useManualBalancesApi();
      const balances: ManualBalance[] = [
        {
          identifier: 42,
          amount: bigNumberify('2.5'),
          asset: 'ETH',
          balanceType: BalanceType.ASSET,
          label: 'Updated Wallet',
          location: 'blockchain',
          tags: ['updated'],
        },
      ];

      const result = await editManualBalances(balances);

      expect(capturedBody).toEqual({
        async_query: true,
        balances: [
          {
            identifier: 42,
            amount: '2.5',
            asset: 'ETH',
            balance_type: 'asset',
            label: 'Updated Wallet',
            location: 'blockchain',
            tags: ['updated'],
          },
        ],
      });
      expect(result.taskId).toBe(200);
    });

    it('throws error on failure', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/balances/manual`, () =>
          HttpResponse.json({
            result: null,
            message: 'Balance not found',
          })),
      );

      const { editManualBalances } = useManualBalancesApi();

      await expect(editManualBalances([]))
        .rejects
        .toThrow('Balance not found');
    });
  });

  describe('deleteManualBalances', () => {
    it('sends DELETE request with ids in body', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/balances/manual`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              balances: [
                {
                  identifier: 1,
                  amount: '1.0',
                  asset: 'ETH',
                  balance_type: 'asset',
                  label: 'Remaining Balance',
                  location: 'blockchain',
                  tags: null,
                  usd_value: '2000.00',
                  value: '2000.00',
                },
              ],
            },
            message: '',
          });
        }),
      );

      const { deleteManualBalances } = useManualBalancesApi();
      const result = await deleteManualBalances([42, 43, 44]);

      expect(capturedBody).toEqual({
        ids: [42, 43, 44],
      });
      expect(result.balances).toHaveLength(1);
      expect(result.balances[0].identifier).toBe(1);
      expect(result.balances[0].label).toBe('Remaining Balance');
    });

    it('returns empty balances array after deleting all', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/balances/manual`, () =>
          HttpResponse.json({
            result: {
              balances: [],
            },
            message: '',
          })),
      );

      const { deleteManualBalances } = useManualBalancesApi();
      const result = await deleteManualBalances([1]);

      expect(result.balances).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/balances/manual`, () =>
          HttpResponse.json({
            result: null,
            message: 'Cannot delete balance',
          })),
      );

      const { deleteManualBalances } = useManualBalancesApi();

      await expect(deleteManualBalances([999]))
        .rejects
        .toThrow('Cannot delete balance');
    });
  });
});
