import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HTTPStatus } from '@/types/api/http';
import { useCounterpartyMappingApi } from './use-counterparty-mapping-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('modules/asset-manager/counterparty-mapping/use-counterparty-mapping-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useCounterpartyMappingApi', () => {
    describe('fetchAllCounterpartyMapping', () => {
      it('sends POST request with snake_case payload and returns collection', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/assets/counterpartymappings`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [
                  {
                    counterparty: 'uniswap',
                    counterparty_symbol: 'WETH',
                    asset: 'ETH',
                  },
                ],
                entries_found: 1,
                entries_limit: 10,
                entries_total: 1,
              },
              message: '',
            });
          }),
        );

        const { fetchAllCounterpartyMapping } = useCounterpartyMappingApi();
        const result = await fetchAllCounterpartyMapping({
          limit: 10,
          offset: 0,
        });

        expect(capturedBody).toEqual({
          limit: 10,
          offset: 0,
        });

        expect(result.data).toHaveLength(1);
        expect(result.data[0].counterpartySymbol).toBe('WETH');
        expect(result.data[0].asset).toBe('ETH');
      });

      it('omits orderByAttributes and ascending from payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/assets/counterpartymappings`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [],
                entries_found: 0,
                entries_limit: 10,
                entries_total: 0,
              },
              message: '',
            });
          }),
        );

        const { fetchAllCounterpartyMapping } = useCounterpartyMappingApi();
        await fetchAllCounterpartyMapping({
          limit: 10,
          offset: 0,
          orderByAttributes: ['counterpartySymbol'],
          ascending: [true],
        });

        expect(capturedBody).toEqual({
          limit: 10,
          offset: 0,
        });
        expect(capturedBody).not.toHaveProperty('order_by_attributes');
        expect(capturedBody).not.toHaveProperty('ascending');
      });
    });

    describe('addCounterpartyMapping', () => {
      it('sends PUT request with entries array', async () => {
        let capturedBody: unknown;

        server.use(
          http.put(`${backendUrl}/api/1/assets/counterpartymappings`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { addCounterpartyMapping } = useCounterpartyMappingApi();
        const result = await addCounterpartyMapping({
          counterparty: 'aave',
          counterpartySymbol: 'USDC',
          asset: 'USDC',
        });

        expect(capturedBody).toEqual({
          entries: [
            {
              counterparty: 'aave',
              counterparty_symbol: 'USDC',
              asset: 'USDC',
            },
          ],
        });
        expect(result).toBe(true);
      });
    });

    describe('editCounterpartyMapping', () => {
      it('sends PATCH request with entries array', async () => {
        let capturedBody: unknown;

        server.use(
          http.patch(`${backendUrl}/api/1/assets/counterpartymappings`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { editCounterpartyMapping } = useCounterpartyMappingApi();
        const result = await editCounterpartyMapping({
          counterparty: 'sushiswap',
          counterpartySymbol: 'WETH',
          asset: 'ETH',
        });

        expect(capturedBody).toEqual({
          entries: [
            {
              counterparty: 'sushiswap',
              counterparty_symbol: 'WETH',
              asset: 'ETH',
            },
          ],
        });
        expect(result).toBe(true);
      });
    });

    describe('deleteCounterpartyMapping', () => {
      it('sends DELETE request with entries array in body', async () => {
        let capturedBody: unknown;

        server.use(
          http.delete(`${backendUrl}/api/1/assets/counterpartymappings`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { deleteCounterpartyMapping } = useCounterpartyMappingApi();
        const result = await deleteCounterpartyMapping({
          counterparty: 'uniswap',
          counterpartySymbol: 'WETH',
        });

        expect(capturedBody).toEqual({
          entries: [
            {
              counterparty: 'uniswap',
              counterparty_symbol: 'WETH',
            },
          ],
        });
        expect(result).toBe(true);
      });

      it('throws error on failure', async () => {
        server.use(
          http.delete(`${backendUrl}/api/1/assets/counterpartymappings`, () =>
            HttpResponse.json({
              result: null,
              message: 'Mapping not found',
            }, { status: HTTPStatus.BAD_REQUEST })),
        );

        const { deleteCounterpartyMapping } = useCounterpartyMappingApi();

        await expect(deleteCounterpartyMapping({
          counterparty: 'unknown',
          counterpartySymbol: 'INVALID',
        }))
          .rejects
          .toThrow();
      });
    });
  });
});
