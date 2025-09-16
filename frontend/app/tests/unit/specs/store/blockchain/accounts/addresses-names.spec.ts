import type { Collection } from '@/types/collection';
import type { AddressBookEntry, AddressBookSimplePayload } from '@/types/eth-names';
import { Blockchain } from '@rotki/common';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAddressesNamesApi } from '@/composables/api/blockchain/addresses-names';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { getDefaultFrontendSettings } from '@/types/settings/frontend-settings';

vi.mock('@/composables/api/blockchain/addresses-names', async () => {
  const { defaultCollectionState } = await import('@/utils/collection');
  return ({
    useAddressesNamesApi: vi.fn().mockReturnValue({
      getEnsNamesTask: vi.fn().mockResolvedValue({ taskId: 1 }),
      getEnsNames: vi.fn().mockResolvedValue({}),
      fetchAddressBook: vi.fn().mockResolvedValue(defaultCollectionState()),
      addAddressBook: vi.fn().mockResolvedValue(true),
      updateAddressBook: vi.fn().mockResolvedValue(true),
      deleteAddressBook: vi.fn().mockResolvedValue(true),
      getAddressesNames: vi.fn().mockResolvedValue([]),
    }),
  });
});

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({ result: {} }),
  }),
}));

vi.mock('@/composables/info/chains', async () => {
  const { ref } = await import('vue');
  return ({
    useSupportedChains: vi.fn().mockReturnValue({
      isEvm: vi.fn().mockReturnValue(ref(true)),
    }),
  });
});

describe('store::blockchain/accounts/addresses-names', () => {
  let store: ReturnType<typeof useAddressesNamesStore>;
  let api: ReturnType<typeof useAddressesNamesApi>;
  setActivePinia(createPinia());

  beforeEach(() => {
    vi.useFakeTimers();
    store = useAddressesNamesStore();
    api = useAddressesNamesApi();
    vi.clearAllMocks();
  });

  describe('fetchEnsNames', () => {
    const addresses: AddressBookSimplePayload[] = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        blockchain: Blockchain.ETH,
      },
    ];

    it('no addresses', async () => {
      await store.fetchEnsNames([]);
      expect(api.getEnsNames).not.toHaveBeenCalled();
    });

    it('with addresses, forceUpdate=false', async () => {
      await store.fetchEnsNames(addresses, false);

      expect(api.getEnsNames).toHaveBeenCalledWith(addresses.map(({ address }) => address));
    });

    it('with same addresses, forceUpdate=true', async () => {
      await store.fetchEnsNames(addresses, true);

      expect(api.getEnsNamesTask).toHaveBeenCalledWith(addresses.map(({ address }) => address));
    });

    it('filter invalid addresses, forceUpdate=true', async () => {
      await store.fetchEnsNames([...addresses, { address: '0xinvalid', blockchain: Blockchain.ETH }], true);

      expect(api.getEnsNamesTask).toHaveBeenCalledWith(addresses.map(({ address }) => address));
    });
  });

  describe('fetchAddressBook', () => {
    const address = ['0x4585FE77225b41b697C938B01232131231231233'];
    const payload = {
      address,
      limit: 10,
      offset: 0,
    };
    const addressesWithEns: AddressBookEntry[] = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        name: 'test.eth',
        blockchain: Blockchain.ETH,
      },
    ];

    const collection: Collection<AddressBookEntry> = {
      data: addressesWithEns,
      limit: 0,
      found: 1,
      total: 1,
    };

    it('location=global', async () => {
      vi.mocked(api.fetchAddressBook).mockResolvedValue(collection);

      const result = await store.getAddressBook('global', payload);

      expect(api.fetchAddressBook).toHaveBeenCalledWith('global', payload);

      expect(result).toEqual(collection);
    });

    it('location=private', async () => {
      vi.mocked(api.fetchAddressBook).mockResolvedValue(collection);

      const result = await store.getAddressBook('private', payload);

      expect(api.fetchAddressBook).toHaveBeenCalledWith('private', payload);

      expect(result).toEqual(collection);
    });
  });

  describe('addAddressBook', () => {
    const entries = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        name: 'test_name',
        blockchain: Blockchain.ETH,
      },
    ];

    it('default', async () => {
      await store.addAddressBook('global', entries, false);

      expect(api.addAddressBook).toHaveBeenCalledWith('global', entries, false);

      await store.addAddressBook('private', entries, true);

      expect(api.addAddressBook).toHaveBeenCalledWith('private', entries, true);
    });
  });

  describe('updateAddressBook', () => {
    const entries = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        name: 'test_name',
        blockchain: Blockchain.ETH,
      },
    ];

    it('default', async () => {
      await store.updateAddressBook('global', entries);

      expect(api.updateAddressBook).toHaveBeenCalledWith('global', entries);

      await store.updateAddressBook('private', entries);

      expect(api.updateAddressBook).toHaveBeenCalledWith('private', entries);
    });
  });

  describe('deleteAddressBook', () => {
    const addresses = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        blockchain: Blockchain.ETH,
      },
    ];

    it('default', async () => {
      await store.deleteAddressBook('global', addresses);

      expect(api.deleteAddressBook).toHaveBeenCalledWith('global', addresses);

      await store.deleteAddressBook('private', addresses);

      expect(api.deleteAddressBook).toHaveBeenCalledWith('private', addresses);
    });
  });

  describe('addressNameSelector', () => {
    const mockedResult = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        blockchain: Blockchain.ETH,
        name: 'test_name',
      },
      {
        address: '0x4585FE77225b41b697C938B01232131231231231',
        blockchain: Blockchain.ETH,
        name: 'test1.eth',
      },
    ];

    it('enableAliasNames=true', async () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        enableAliasNames: true,
      });

      vi.mocked(api.getAddressesNames).mockResolvedValue(mockedResult);
      const firstAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231233');

      const secondAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231231');

      expect(get(firstAddressName)).toEqual(undefined);
      expect(get(secondAddressName)).toEqual(undefined);

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).toHaveBeenCalledOnce();

      expect(get(firstAddressName)).toEqual('test_name');
      expect(get(secondAddressName)).toEqual('test1.eth');
    });

    it('use the value from cache if addresses names has been fetched before', async () => {
      const firstAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231233');

      const secondAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231231');

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).not.toHaveBeenCalled();

      expect(get(firstAddressName)).toEqual('test_name');
      expect(get(secondAddressName)).toEqual('test1.eth');
    });

    it('enableAliasNames=false', async () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        enableAliasNames: false,
      });

      const firstAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231233');

      const secondAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231231');

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).not.toHaveBeenCalled();

      expect(get(firstAddressName)).toEqual(undefined);
      expect(get(secondAddressName)).toEqual(undefined);
    });
  });
});
