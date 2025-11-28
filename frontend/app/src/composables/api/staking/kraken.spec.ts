import { BigNumber } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useKrakenApi } from './kraken';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/staking/kraken', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('refreshKrakenStaking', () => {
    it('sends async POST request with empty pagination', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/staking/kraken`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { refreshKrakenStaking } = useKrakenApi();
      const result = await refreshKrakenStaking();

      expect(capturedBody).toEqual({
        async_query: true,
        ascending: [false],
        limit: 0,
        offset: 0,
        order_by_attributes: ['timestamp'],
      });
      expect(result.taskId).toBe(123);
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/staking/kraken`, () =>
          HttpResponse.json({
            result: null,
            message: 'Kraken staking refresh failed',
          })),
      );

      const { refreshKrakenStaking } = useKrakenApi();

      await expect(refreshKrakenStaking())
        .rejects
        .toThrow('Kraken staking refresh failed');
    });
  });

  describe('fetchKrakenStakingEvents', () => {
    it('fetches staking events with only_cache true', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/staking/kraken`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              assets: ['ETH', 'DOT'],
              entries_found: 10,
              entries_limit: 100,
              entries_total: 50,
              received: [
                { asset: 'ETH', amount: '1.5', usd_value: '3000' },
                { asset: 'DOT', amount: '100', usd_value: '500' },
              ],
              total_usd_value: '3500',
            },
            message: '',
          });
        }),
      );

      const { fetchKrakenStakingEvents } = useKrakenApi();
      const result = await fetchKrakenStakingEvents({
        limit: 10,
        offset: 0,
        orderByAttributes: ['timestamp'],
        ascending: [false],
      });

      expect(capturedBody).toEqual({
        async_query: false,
        limit: 10,
        offset: 0,
        order_by_attributes: ['timestamp'],
        ascending: [false],
        only_cache: true,
      });
      expect(result.assets).toEqual(['ETH', 'DOT']);
      expect(result.entriesFound).toBe(10);
      expect(result.entriesTotal).toBe(50);
      expect(result.received).toHaveLength(2);
      expect(result.totalUsdValue).toBeInstanceOf(BigNumber);
      expect(result.totalUsdValue.toString()).toBe('3500');
    });

    it('handles pagination with filters', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/staking/kraken`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              assets: ['ETH'],
              entries_found: 5,
              entries_limit: 50,
              entries_total: 20,
              received: [
                { asset: 'ETH', amount: '0.5', usd_value: '1000' },
              ],
              total_usd_value: '1000',
            },
            message: '',
          });
        }),
      );

      const { fetchKrakenStakingEvents } = useKrakenApi();
      await fetchKrakenStakingEvents({
        limit: 50,
        offset: 10,
        orderByAttributes: ['timestamp', 'eventType'],
        ascending: [true, false],
        fromTimestamp: 1700000000,
        toTimestamp: 1700100000,
        asset: 'ETH',
        eventSubtypes: ['reward'],
      });

      expect(capturedBody).toEqual({
        async_query: false,
        limit: 50,
        offset: 10,
        order_by_attributes: ['timestamp', 'event_type'],
        ascending: [true, false],
        from_timestamp: 1700000000,
        to_timestamp: 1700100000,
        asset: 'ETH',
        event_subtypes: ['reward'],
        only_cache: true,
      });
    });

    it('handles empty results', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/staking/kraken`, () =>
          HttpResponse.json({
            result: {
              assets: [],
              entries_found: 0,
              entries_limit: 100,
              entries_total: 0,
              received: [],
              total_usd_value: '0',
            },
            message: '',
          })),
      );

      const { fetchKrakenStakingEvents } = useKrakenApi();
      const result = await fetchKrakenStakingEvents({
        limit: 10,
        offset: 0,
        orderByAttributes: ['timestamp'],
        ascending: [false],
      });

      expect(result.assets).toEqual([]);
      expect(result.entriesFound).toBe(0);
      expect(result.received).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/staking/kraken`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch staking events',
          })),
      );

      const { fetchKrakenStakingEvents } = useKrakenApi();

      await expect(fetchKrakenStakingEvents({
        limit: 10,
        offset: 0,
        orderByAttributes: ['timestamp'],
        ascending: [false],
      }))
        .rejects
        .toThrow('Failed to fetch staking events');
    });
  });
});
