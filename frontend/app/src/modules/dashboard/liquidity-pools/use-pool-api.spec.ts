import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePoolApi } from './use-pool-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('modules/dashboard/liquidity-pools/use-pool-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getUniswapV2Balances', () => {
    it('fetches uniswap v2 balances as async task', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/uniswap/v2/balances`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 1,
            },
            message: '',
          });
        }),
      );

      const { getUniswapV2Balances } = usePoolApi();
      const result = await getUniswapV2Balances();

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(1);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/uniswap/v2/balances`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch uniswap v2 balances',
          })),
      );

      const { getUniswapV2Balances } = usePoolApi();

      await expect(getUniswapV2Balances())
        .rejects
        .toThrow('Failed to fetch uniswap v2 balances');
    });
  });

  describe('getSushiswapBalances', () => {
    it('fetches sushiswap balances as async task', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/sushiswap/balances`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 2,
            },
            message: '',
          });
        }),
      );

      const { getSushiswapBalances } = usePoolApi();
      const result = await getSushiswapBalances();

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(2);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/sushiswap/balances`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch sushiswap balances',
          })),
      );

      const { getSushiswapBalances } = usePoolApi();

      await expect(getSushiswapBalances())
        .rejects
        .toThrow('Failed to fetch sushiswap balances');
    });
  });
});
