import { BigNumber } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWrapStatisticsApi } from './wrap';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/statistics/wrap', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchWrapStatistics', () => {
    it('fetches wrap statistics with timestamp params', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/statistics/events`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              eth_on_gas: '1.5',
              eth_on_gas_per_address: {
                '0x1234': '0.5',
                '0x5678': '1.0',
              },
              gnosis_max_payments_by_currency: [
                { amount: '100', symbol: 'EUR' },
                { amount: '50', symbol: 'USD' },
              ],
              score: 85,
              top_days_by_number_of_transactions: [
                { amount: '15', timestamp: 1700000000 },
                { amount: '10', timestamp: 1700100000 },
              ],
              trades_by_exchange: {
                binance: '25',
                kraken: '10',
              },
              transactions_per_chain: {
                ethereum: '100',
                optimism: '50',
              },
              transactions_per_protocol: [
                { protocol: 'uniswap', transactions: '30' },
                { protocol: 'aave', transactions: '20' },
              ],
            },
            message: '',
          });
        }),
      );

      const { fetchWrapStatistics } = useWrapStatisticsApi();
      const result = await fetchWrapStatistics({
        start: 1700000000,
        end: 1700100000,
      });

      expect(capturedBody).toEqual({
        from_timestamp: 1700000000,
        to_timestamp: 1700100000,
      });
      expect(result.ethOnGas).toBeInstanceOf(BigNumber);
      expect(result.ethOnGas.toString()).toBe('1.5');
      expect(result.ethOnGasPerAddress['0x1234']).toBeInstanceOf(BigNumber);
      expect(result.ethOnGasPerAddress['0x1234'].toString()).toBe('0.5');
      expect(result.gnosisMaxPaymentsByCurrency).toHaveLength(2);
      expect(result.gnosisMaxPaymentsByCurrency[0].symbol).toBe('EUR');
      expect(result.score).toBe(85);
      expect(result.topDaysByNumberOfTransactions).toHaveLength(2);
      expect(result.tradesByExchange.binance).toBeInstanceOf(BigNumber);
      expect(result.tradesByExchange.binance.toString()).toBe('25');
      expect(result.transactionsPerChain.ethereum).toBeInstanceOf(BigNumber);
      expect(result.transactionsPerChain.ethereum.toString()).toBe('100');
      expect(result.transactionsPerProtocol).toHaveLength(2);
      expect(result.transactionsPerProtocol[0].protocol).toBe('uniswap');
    });

    it('handles empty statistics', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/statistics/events`, () =>
          HttpResponse.json({
            result: {
              eth_on_gas: '0',
              eth_on_gas_per_address: {},
              gnosis_max_payments_by_currency: [],
              score: 0,
              top_days_by_number_of_transactions: [],
              trades_by_exchange: {},
              transactions_per_chain: {},
              transactions_per_protocol: [],
            },
            message: '',
          })),
      );

      const { fetchWrapStatistics } = useWrapStatisticsApi();
      const result = await fetchWrapStatistics({
        start: 1700000000,
        end: 1700100000,
      });

      expect(result.ethOnGas).toBeInstanceOf(BigNumber);
      expect(result.ethOnGas.toString()).toBe('0');
      expect(result.ethOnGasPerAddress).toEqual({});
      expect(result.gnosisMaxPaymentsByCurrency).toEqual([]);
      expect(result.score).toBe(0);
      expect(result.topDaysByNumberOfTransactions).toEqual([]);
      expect(result.tradesByExchange).toEqual({});
      expect(result.transactionsPerChain).toEqual({});
      expect(result.transactionsPerProtocol).toEqual([]);
    });

    it('throws error on null result', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/statistics/events`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch wrap statistics',
          })),
      );

      const { fetchWrapStatistics } = useWrapStatisticsApi();

      await expect(fetchWrapStatistics({
        start: 1700000000,
        end: 1700100000,
      }))
        .rejects
        .toThrow('Failed to fetch wrap statistics');
    });

    it('throws error on invalid response format', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/statistics/events`, () =>
          HttpResponse.json({
            result: { invalid: 'format' },
            message: '',
          })),
      );

      const { fetchWrapStatistics } = useWrapStatisticsApi();

      await expect(fetchWrapStatistics({
        start: 1700000000,
        end: 1700100000,
      }))
        .rejects
        .toThrow(); // Zod validation error
    });
  });
});
