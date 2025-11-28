import type { AddressBookEntry, AddressBookLocation, AddressBookSimplePayload } from '@/types/eth-names';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAddressesNamesApi } from './addresses-names';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/blockchain/addresses-names', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getEnsNamesTask', () => {
    it('gets ENS names as async task', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/names/ens/reverse`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { getEnsNamesTask } = useAddressesNamesApi();
      const result = await getEnsNamesTask(['0x123', '0x456']);

      expect(capturedBody).toEqual({
        async_query: true,
        ethereum_addresses: ['0x123', '0x456'],
        ignore_cache: true,
      });
      expect(result.taskId).toBe(123);
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/names/ens/reverse`, () =>
          HttpResponse.json({
            result: null,
            message: 'ENS service unavailable',
          })),
      );

      const { getEnsNamesTask } = useAddressesNamesApi();

      await expect(getEnsNamesTask(['0x123']))
        .rejects
        .toThrow('ENS service unavailable');
    });
  });

  describe('getEnsNames', () => {
    it('gets ENS names synchronously', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/names/ens/reverse`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              '0x123': 'vitalik.eth',
              '0x456': null,
            },
            message: '',
          });
        }),
      );

      const { getEnsNames } = useAddressesNamesApi();
      const result = await getEnsNames(['0x123', '0x456']);

      expect(capturedBody).toEqual({
        async_query: false,
        ethereum_addresses: ['0x123', '0x456'],
        ignore_cache: false,
      });
      expect(result['0x123']).toBe('vitalik.eth');
      expect(result['0x456']).toBeNull();
    });
  });

  describe('resolveEnsNames', () => {
    it('resolves ENS name to address', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/names/ens/resolve`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045',
            message: '',
          });
        }),
      );

      const { resolveEnsNames } = useAddressesNamesApi();
      const result = await resolveEnsNames('vitalik.eth');

      expect(capturedBody).toEqual({ name: 'vitalik.eth' });
      expect(result).toBe('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045');
    });

    it('returns empty string when name not found', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/names/ens/resolve`, () =>
          HttpResponse.json({
            result: null,
            message: '',
          })),
      );

      const { resolveEnsNames } = useAddressesNamesApi();
      const result = await resolveEnsNames('nonexistent.eth');

      expect(result).toBe('');
    });
  });

  describe('fetchAddressBook', () => {
    it('fetches address book entries', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedLocation: string | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/names/addressbook/:location`, async ({ request, params }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          capturedLocation = params.location as string;
          return HttpResponse.json({
            result: {
              entries: [
                { address: '0x123', blockchain: 'eth', name: 'Alice' },
                { address: '0x456', blockchain: 'eth', name: 'Bob' },
              ],
              entries_found: 2,
              entries_total: 2,
              entries_limit: -1,
            },
            message: '',
          });
        }),
      );

      const { fetchAddressBook } = useAddressesNamesApi();
      const location: AddressBookLocation = 'global';
      const result = await fetchAddressBook(location, {
        limit: 10,
        offset: 0,
      });

      expect(capturedLocation).toBe('global');
      expect(capturedBody).toMatchObject({
        limit: 10,
        offset: 0,
      });
      expect(result.data).toHaveLength(2);
      expect(result.data[0].name).toBe('Alice');
      expect(result.found).toBe(2);
      expect(result.total).toBe(2);
    });

    it('supports filtering by addresses', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/names/addressbook/:location`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              entries: [
                { address: '0x123', blockchain: 'eth', name: 'Alice' },
              ],
              entries_found: 1,
              entries_total: 1,
              entries_limit: -1,
            },
            message: '',
          });
        }),
      );

      const { fetchAddressBook } = useAddressesNamesApi();
      await fetchAddressBook('private', {
        limit: 10,
        offset: 0,
        address: ['0x123'],
      });

      expect(capturedBody).toMatchObject({
        addresses: [{ address: '0x123' }],
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/names/addressbook/:location`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch address book',
          })),
      );

      const { fetchAddressBook } = useAddressesNamesApi();

      await expect(fetchAddressBook('global', { limit: 10, offset: 0 }))
        .rejects
        .toThrow('Failed to fetch address book');
    });
  });

  describe('addAddressBook', () => {
    it('adds address book entries', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedLocation: string | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/names/addressbook/:location`, async ({ request, params }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          capturedLocation = params.location as string;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { addAddressBook } = useAddressesNamesApi();
      const entries: AddressBookEntry[] = [
        { address: '0x123', blockchain: 'eth', name: 'Alice' },
      ];
      const result = await addAddressBook('global', entries);

      expect(capturedLocation).toBe('global');
      expect(capturedBody).toEqual({
        entries: [{ address: '0x123', blockchain: 'eth', name: 'Alice' }],
        update_existing: false,
      });
      expect(result).toBe(true);
    });

    it('supports update_existing flag', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/names/addressbook/:location`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { addAddressBook } = useAddressesNamesApi();
      const entries: AddressBookEntry[] = [
        { address: '0x123', blockchain: 'eth', name: 'Alice Updated' },
      ];
      await addAddressBook('global', entries, true);

      expect(capturedBody).toMatchObject({
        update_existing: true,
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/names/addressbook/:location`, () =>
          HttpResponse.json({
            result: null,
            message: 'Entry already exists',
          })),
      );

      const { addAddressBook } = useAddressesNamesApi();

      await expect(addAddressBook('global', []))
        .rejects
        .toThrow('Entry already exists');
    });
  });

  describe('updateAddressBook', () => {
    it('updates address book entries', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/names/addressbook/:location`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { updateAddressBook } = useAddressesNamesApi();
      const entries: AddressBookEntry[] = [
        { address: '0x123', blockchain: 'eth', name: 'Alice Updated' },
      ];
      const result = await updateAddressBook('private', entries);

      expect(capturedBody).toEqual({
        entries: [{ address: '0x123', blockchain: 'eth', name: 'Alice Updated' }],
      });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/names/addressbook/:location`, () =>
          HttpResponse.json({
            result: null,
            message: 'Entry not found',
          })),
      );

      const { updateAddressBook } = useAddressesNamesApi();

      await expect(updateAddressBook('global', []))
        .rejects
        .toThrow('Entry not found');
    });
  });

  describe('deleteAddressBook', () => {
    it('deletes address book entries', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/names/addressbook/:location`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteAddressBook } = useAddressesNamesApi();
      const addresses: AddressBookSimplePayload[] = [
        { address: '0x123', blockchain: 'eth' },
      ];
      const result = await deleteAddressBook('global', addresses);

      expect(capturedBody).toEqual({
        addresses: [{ address: '0x123', blockchain: 'eth' }],
      });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/names/addressbook/:location`, () =>
          HttpResponse.json({
            result: null,
            message: 'Entry not found',
          })),
      );

      const { deleteAddressBook } = useAddressesNamesApi();

      await expect(deleteAddressBook('global', []))
        .rejects
        .toThrow('Entry not found');
    });
  });

  describe('getAddressesNames', () => {
    it('gets names for addresses', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/names`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: [
              { address: '0x123', blockchain: 'eth', name: 'Alice' },
              { address: '0x456', blockchain: 'eth', name: 'Bob' },
            ],
            message: '',
          });
        }),
      );

      const { getAddressesNames } = useAddressesNamesApi();
      const addresses: AddressBookSimplePayload[] = [
        { address: '0x123', blockchain: 'eth' },
        { address: '0x456', blockchain: 'eth' },
      ];
      const result = await getAddressesNames(addresses);

      expect(capturedBody).toEqual({
        addresses: [
          { address: '0x123', blockchain: 'eth' },
          { address: '0x456', blockchain: 'eth' },
        ],
      });
      expect(result).toHaveLength(2);
      expect(result[0].name).toBe('Alice');
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/names`, () =>
          HttpResponse.json({
            result: null,
            message: 'Service unavailable',
          })),
      );

      const { getAddressesNames } = useAddressesNamesApi();

      await expect(getAddressesNames([]))
        .rejects
        .toThrow('Service unavailable');
    });
  });

  describe('ensAvatarUrl', () => {
    it('generates avatar URL without timestamp', () => {
      const { ensAvatarUrl } = useAddressesNamesApi();
      const url = ensAvatarUrl('vitalik.eth');

      expect(url).toBe(`${backendUrl}/api/1/avatars/ens/vitalik.eth`);
    });

    it('generates avatar URL with timestamp', () => {
      const { ensAvatarUrl } = useAddressesNamesApi();
      const url = ensAvatarUrl('vitalik.eth', 1700000000);

      expect(url).toBe(`${backendUrl}/api/1/avatars/ens/vitalik.eth?timestamp=1700000000`);
    });
  });

  describe('clearEnsAvatarCache', () => {
    it('clears specific ENS avatar cache', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/cache/avatars/clear`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { clearEnsAvatarCache } = useAddressesNamesApi();
      const result = await clearEnsAvatarCache(['vitalik.eth', 'alice.eth']);

      expect(capturedBody).toEqual({
        entries: ['vitalik.eth', 'alice.eth'],
      });
      expect(result).toBe(true);
    });

    it('clears all ENS avatar cache when null', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/cache/avatars/clear`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { clearEnsAvatarCache } = useAddressesNamesApi();
      const result = await clearEnsAvatarCache(null);

      expect(capturedBody).toEqual({
        entries: null,
      });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/cache/avatars/clear`, () =>
          HttpResponse.json({
            result: null,
            message: 'Cache clear failed',
          })),
      );

      const { clearEnsAvatarCache } = useAddressesNamesApi();

      await expect(clearEnsAvatarCache(null))
        .rejects
        .toThrow('Cache clear failed');
    });
  });
});
