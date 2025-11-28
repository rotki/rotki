import type { QueriedAddressPayload } from '@/types/session';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Module } from '@/types/modules';

vi.unmock('@/composables/api/session/queried-addresses');

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/session/queried-addresses', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function getApi(): Promise<ReturnType<typeof import('./queried-addresses').useQueriedAddressApi>> {
    const { useQueriedAddressApi } = await import('./queried-addresses');
    return useQueriedAddressApi();
  }

  describe('queriedAddresses', () => {
    it('gets queried addresses', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/queried_addresses`, () =>
          HttpResponse.json({
            result: {
              makerdao_dsr: ['0x123', '0x456'],
              uniswap: ['0x789'],
            },
            message: '',
          })),
      );

      const { queriedAddresses } = await getApi();
      const result = await queriedAddresses();

      expect(result.makerdaoDsr).toEqual(['0x123', '0x456']);
      expect(result.uniswap).toEqual(['0x789']);
    });

    it('returns empty object when no addresses are configured', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/queried_addresses`, () =>
          HttpResponse.json({
            result: {},
            message: '',
          })),
      );

      const { queriedAddresses } = await getApi();
      const result = await queriedAddresses();

      expect(result).toEqual({});
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/queried_addresses`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to get queried addresses',
          })),
      );

      const { queriedAddresses } = await getApi();

      await expect(queriedAddresses())
        .rejects
        .toThrow('Failed to get queried addresses');
    });
  });

  describe('addQueriedAddress', () => {
    it('adds a queried address', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/queried_addresses`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              makerdao_dsr: ['0x123', '0x456', '0x789'],
            },
            message: '',
          });
        }),
      );

      const { addQueriedAddress } = await getApi();
      const payload: QueriedAddressPayload = {
        module: Module.MAKERDAO_DSR,
        address: '0x789',
      };
      const result = await addQueriedAddress(payload);

      expect(capturedBody).toEqual({
        module: 'makerdao_dsr',
        address: '0x789',
      });
      expect(result.makerdaoDsr).toEqual(['0x123', '0x456', '0x789']);
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/queried_addresses`, () =>
          HttpResponse.json({
            result: null,
            message: 'Address already exists',
          })),
      );

      const { addQueriedAddress } = await getApi();
      const payload: QueriedAddressPayload = {
        module: Module.MAKERDAO_DSR,
        address: '0x123',
      };

      await expect(addQueriedAddress(payload))
        .rejects
        .toThrow('Address already exists');
    });
  });

  describe('deleteQueriedAddress', () => {
    it('deletes a queried address', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/queried_addresses`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              makerdao_dsr: ['0x123'],
            },
            message: '',
          });
        }),
      );

      const { deleteQueriedAddress } = await getApi();
      const payload: QueriedAddressPayload = {
        module: Module.MAKERDAO_DSR,
        address: '0x456',
      };
      const result = await deleteQueriedAddress(payload);

      expect(capturedBody).toEqual({
        module: 'makerdao_dsr',
        address: '0x456',
      });
      expect(result.makerdaoDsr).toEqual(['0x123']);
    });

    it('returns empty array when last address is deleted', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/queried_addresses`, () =>
          HttpResponse.json({
            result: {
              makerdao_dsr: [],
            },
            message: '',
          })),
      );

      const { deleteQueriedAddress } = await getApi();
      const payload: QueriedAddressPayload = {
        module: Module.MAKERDAO_DSR,
        address: '0x123',
      };
      const result = await deleteQueriedAddress(payload);

      expect(result.makerdaoDsr).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/queried_addresses`, () =>
          HttpResponse.json({
            result: null,
            message: 'Address not found',
          })),
      );

      const { deleteQueriedAddress } = await getApi();
      const payload: QueriedAddressPayload = {
        module: Module.MAKERDAO_DSR,
        address: '0x999',
      };

      await expect(deleteQueriedAddress(payload))
        .rejects
        .toThrow('Address not found');
    });
  });
});
