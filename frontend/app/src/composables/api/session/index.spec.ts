import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionApi } from './index';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/session/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('consumeMessages', () => {
    it('should fetch and returns messages', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/messages`, () =>
          HttpResponse.json({
            result: {
              errors: ['Error 1', 'Error 2'],
              warnings: ['Warning 1'],
            },
            message: '',
          })),
      );

      const { consumeMessages } = useSessionApi();
      const result = await consumeMessages();

      expect(result.errors).toEqual(['Error 1', 'Error 2']);
      expect(result.warnings).toEqual(['Warning 1']);
    });

    it('should handle empty messages', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/messages`, () =>
          HttpResponse.json({
            result: {
              errors: [],
              warnings: [],
            },
            message: '',
          })),
      );

      const { consumeMessages } = useSessionApi();
      const result = await consumeMessages();

      expect(result.errors).toEqual([]);
      expect(result.warnings).toEqual([]);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/messages`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to consume messages',
          })),
      );

      const { consumeMessages } = useSessionApi();

      await expect(consumeMessages())
        .rejects
        .toThrow('Failed to consume messages');
    });
  });

  describe('fetchPeriodicData', () => {
    it('should fetch and parses periodic data', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/periodic`, () =>
          HttpResponse.json({
            result: {
              connected_nodes: {
                ethereum: ['node1', 'node2'],
                optimism: ['op_node1'],
              },
              cooling_down_nodes: {
                ethereum: ['node3'],
              },
              failed_to_connect: {
                arbitrum: ['arb_node1'],
              },
              last_balance_save: 1700000000,
              last_data_upload_ts: 1700100000,
            },
            message: '',
          })),
      );

      const { fetchPeriodicData } = useSessionApi();
      const result = await fetchPeriodicData();

      expect(result.connectedNodes.ethereum).toEqual(['node1', 'node2']);
      expect(result.connectedNodes.optimism).toEqual(['op_node1']);
      expect(result.coolingDownNodes?.ethereum).toEqual(['node3']);
      expect(result.failedToConnect?.arbitrum).toEqual(['arb_node1']);
      expect(result.lastBalanceSave).toBe(1700000000);
      expect(result.lastDataUploadTs).toBe(1700100000);
    });

    it('should handle empty connected nodes', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/periodic`, () =>
          HttpResponse.json({
            result: {
              connected_nodes: {},
              last_balance_save: 0,
              last_data_upload_ts: 0,
            },
            message: '',
          })),
      );

      const { fetchPeriodicData } = useSessionApi();
      const result = await fetchPeriodicData();

      expect(result.connectedNodes).toEqual({});
      expect(result.lastBalanceSave).toBe(0);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/periodic`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch periodic data',
          })),
      );

      const { fetchPeriodicData } = useSessionApi();

      await expect(fetchPeriodicData())
        .rejects
        .toThrow('Failed to fetch periodic data');
    });
  });

  describe('refreshGeneralCacheTask', () => {
    it('should send POST request with snake_case payload', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/protocols/data/refresh`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { refreshGeneralCacheTask } = useSessionApi();
      const result = await refreshGeneralCacheTask('uniswap');

      expect(capturedBody).toEqual({
        async_query: true,
        cache_protocol: 'uniswap',
      });
      expect(result.taskId).toBe(123);
    });

    it('should handle different cache protocols', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/protocols/data/refresh`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { task_id: 456 },
            message: '',
          });
        }),
      );

      const { refreshGeneralCacheTask } = useSessionApi();
      await refreshGeneralCacheTask('aave');

      expect(capturedBody).toHaveProperty('cache_protocol', 'aave');
    });

    it('should throw error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/protocols/data/refresh`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid cache protocol',
          })),
      );

      const { refreshGeneralCacheTask } = useSessionApi();

      await expect(refreshGeneralCacheTask('invalid'))
        .rejects
        .toThrow('Invalid cache protocol');
    });
  });

  describe('getRefreshableGeneralCaches', () => {
    it('should fetch list of refreshable caches', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/protocols/data/refresh`, () =>
          HttpResponse.json({
            result: ['uniswap', 'aave', 'compound', 'makerdao'],
            message: '',
          })),
      );

      const { getRefreshableGeneralCaches } = useSessionApi();
      const result = await getRefreshableGeneralCaches();

      expect(result).toEqual(['uniswap', 'aave', 'compound', 'makerdao']);
    });

    it('should handle empty cache list', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/protocols/data/refresh`, () =>
          HttpResponse.json({
            result: [],
            message: '',
          })),
      );

      const { getRefreshableGeneralCaches } = useSessionApi();
      const result = await getRefreshableGeneralCaches();

      expect(result).toEqual([]);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/protocols/data/refresh`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to get refreshable caches',
          })),
      );

      const { getRefreshableGeneralCaches } = useSessionApi();

      await expect(getRefreshableGeneralCaches())
        .rejects
        .toThrow('Failed to get refreshable caches');
    });
  });
});
