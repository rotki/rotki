import type { FetchBlockchainBalancePayload } from '@/modules/balances/types/blockchain-balances';
import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Module } from '@/modules/common/modules';
import { useBlockchainBalancesApi } from './blockchain';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/balances/blockchain', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('queryLoopringBalances', () => {
    it('should fetch loopring balances with async_query param', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/loopring/balances`, ({ request }) => {
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

      const { queryLoopringBalances } = useBlockchainBalancesApi();
      const result = await queryLoopringBalances();

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(123);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/loopring/balances`, () =>
          HttpResponse.json({
            result: null,
            message: 'Loopring query failed',
          })),
      );

      const { queryLoopringBalances } = useBlockchainBalancesApi();

      await expect(queryLoopringBalances())
        .rejects
        .toThrow('Loopring query failed');
    });
  });

  describe('queryBlockchainBalances', () => {
    it('should fetch all blockchain balances without specific blockchain', async () => {
      let capturedUrl = '';
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances/blockchains/:blockchain`, ({ request }) => {
          capturedUrl = request.url;
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

      const { queryBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = { blockchain: 'btc' };
      const result = await queryBlockchainBalances(payload);

      expect(capturedUrl).toContain('/balances/blockchains/btc');
      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(456);
    });

    it('should fetch specific blockchain balances', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances/blockchains/eth`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 789,
            },
            message: '',
          });
        }),
      );

      const { queryBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = {
        blockchain: 'eth',
      };
      const result = await queryBlockchainBalances(payload);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(789);
    });

    it('should include addresses param', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances/blockchains/eth`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 100,
            },
            message: '',
          });
        }),
      );

      const { queryBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = {
        blockchain: 'eth',
        addresses: ['0x1234', '0x5678'],
      };
      await queryBlockchainBalances(payload);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('addresses')).toBe('0x1234,0x5678');
      expect(capturedParams!.get('ignore_cache')).toBeNull();
    });

    it('should include value_threshold when provided', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances/blockchains`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 200,
            },
            message: '',
          });
        }),
      );

      const { queryBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = { blockchain: '' };
      await queryBlockchainBalances(payload, '1000');

      expect(capturedParams!.get('value_threshold')).toBe('1000');
    });

    it('should throw error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/balances/blockchains`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch balances',
          })),
      );

      const { queryBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = { blockchain: '' };

      await expect(queryBlockchainBalances(payload))
        .rejects
        .toThrow('Failed to fetch balances');
    });
  });

  describe('refreshBlockchainBalances', () => {
    it('should send POST to refresh balances for specific blockchain', async () => {
      let capturedBody: DefaultBodyType = null;
      let capturedUrl = '';

      server.use(
        http.post(`${backendUrl}/api/1/balances/blockchains/eth`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json();
          return HttpResponse.json({
            result: {
              task_id: 500,
            },
            message: '',
          });
        }),
      );

      const { refreshBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = {
        blockchain: 'eth',
        addresses: ['0x1234'],
      };
      const result = await refreshBlockchainBalances(payload);

      expect(capturedUrl).toContain('/balances/blockchains/eth');
      expect(capturedBody).toEqual({
        addresses: ['0x1234'],
        async_query: true,
      });
      expect(result.taskId).toBe(500);
    });

    it('should send POST to refresh all blockchain balances', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/balances/blockchains`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: {
              task_id: 501,
            },
            message: '',
          });
        }),
      );

      const { refreshBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = {
        blockchain: '',
      };
      const result = await refreshBlockchainBalances(payload);

      expect(capturedBody).toEqual({
        async_query: true,
      });
      expect(result.taskId).toBe(501);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/balances/blockchains`, () =>
          HttpResponse.json({
            result: null,
            message: 'Refresh failed',
          })),
      );

      const { refreshBlockchainBalances } = useBlockchainBalancesApi();

      await expect(refreshBlockchainBalances({ blockchain: '' }))
        .rejects
        .toThrow('Refresh failed');
    });
  });

  describe('queryXpubBalances', () => {
    it('should fetch xpub balances for specific blockchain', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/btc/xpub`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 300,
            },
            message: '',
          });
        }),
      );

      const { queryXpubBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = {
        blockchain: 'btc',
        addresses: ['xpub6ABC123...'],
      };
      const result = await queryXpubBalances(payload);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('xpub')).toBe('xpub6ABC123...');
      expect(result.taskId).toBe(300);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/btc/xpub`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid xpub',
          })),
      );

      const { queryXpubBalances } = useBlockchainBalancesApi();

      await expect(queryXpubBalances({ blockchain: 'btc' }))
        .rejects
        .toThrow('Invalid xpub');
    });
  });

  describe('fetchDetectedTokens', () => {
    it('should fetch detected tokens with only_cache param', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/eth/tokens/detect`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: {
              '0x1234': {
                last_update_timestamp: 1700000000,
                tokens: ['0xtoken1', '0xtoken2'],
              },
            },
            message: '',
          });
        }),
      );

      const { fetchDetectedTokens } = useBlockchainBalancesApi();
      const result = await fetchDetectedTokens('eth', ['0x1234']);

      expect(capturedBody).toEqual({
        addresses: ['0x1234'],
        only_cache: true,
      });
      expect(result['0x1234'].tokens).toEqual(['0xtoken1', '0xtoken2']);
    });

    it('should handle null addresses', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/eth/tokens/detect`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: {},
            message: '',
          });
        }),
      );

      const { fetchDetectedTokens } = useBlockchainBalancesApi();
      await fetchDetectedTokens('eth', null);

      expect(capturedBody).toEqual({
        addresses: null,
        only_cache: true,
      });
    });

    it('should throw error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/blockchains/eth/tokens/detect`, () =>
          HttpResponse.json({
            result: null,
            message: 'Token detection failed',
          })),
      );

      const { fetchDetectedTokens } = useBlockchainBalancesApi();

      await expect(fetchDetectedTokens('eth', ['0x1234']))
        .rejects
        .toThrow('Token detection failed');
    });
  });

  describe('fetchDetectedTokensTask', () => {
    it('should fetch detected tokens as async task', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/eth/tokens/detect`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: {
              task_id: 400,
            },
            message: '',
          });
        }),
      );

      const { fetchDetectedTokensTask } = useBlockchainBalancesApi();
      const result = await fetchDetectedTokensTask('eth', ['0x1234', '0x5678']);

      expect(capturedBody).toEqual({
        addresses: ['0x1234', '0x5678'],
        async_query: true,
      });
      expect(result.taskId).toBe(400);
    });
  });

  describe('deleteModuleData', () => {
    it('should delete all module data when no module specified', async () => {
      let capturedUrl = '';

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth/modules/data`, ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteModuleData } = useBlockchainBalancesApi();
      const result = await deleteModuleData();

      expect(capturedUrl).toContain('/blockchains/eth/modules/data');
      expect(result).toBe(true);
    });

    it('should delete specific module data', async () => {
      let capturedUrl = '';

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth/modules/loopring/data`, ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteModuleData } = useBlockchainBalancesApi();
      const result = await deleteModuleData(Module.LOOPRING);

      expect(capturedUrl).toContain('/blockchains/eth/modules/loopring/data');
      expect(result).toBe(true);
    });

    it('should handle null module parameter', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth/modules/data`, () =>
          HttpResponse.json({
            result: true,
            message: '',
          })),
      );

      const { deleteModuleData } = useBlockchainBalancesApi();
      const result = await deleteModuleData(null);

      expect(result).toBe(true);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth/modules/data`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to delete module data',
          })),
      );

      const { deleteModuleData } = useBlockchainBalancesApi();

      await expect(deleteModuleData())
        .rejects
        .toThrow('Failed to delete module data');
    });
  });
});
