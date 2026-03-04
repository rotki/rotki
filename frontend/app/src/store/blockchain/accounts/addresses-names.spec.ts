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

describe('useAddressesNamesStore', () => {
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

    it('should handle no addresses', async () => {
      await store.fetchEnsNames([]);
      expect(api.getEnsNames).not.toHaveBeenCalled();
    });

    it('should handle addresses with forceUpdate disabled', async () => {
      await store.fetchEnsNames(addresses, false);

      expect(api.getEnsNames).toHaveBeenCalledWith(addresses.map(({ address }) => address));
    });

    it('should handle same addresses with forceUpdate enabled', async () => {
      await store.fetchEnsNames(addresses, true);

      expect(api.getEnsNamesTask).toHaveBeenCalledWith(addresses.map(({ address }) => address));
    });

    it('should filter invalid addresses with forceUpdate enabled', async () => {
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

    it('should handle global location', async () => {
      vi.mocked(api.fetchAddressBook).mockResolvedValue(collection);

      const result = await store.getAddressBook('global', payload);

      expect(api.fetchAddressBook).toHaveBeenCalledWith('global', payload);

      expect(result).toEqual(collection);
    });

    it('should handle private location', async () => {
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

    it('should add address book entry', async () => {
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

    it('should update address book entry', async () => {
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

    it('should delete address book entry', async () => {
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

    it('should handle enableAliasNames when true', async () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        enableAliasNames: true,
      });

      vi.mocked(api.getAddressesNames).mockResolvedValue(mockedResult);
      const firstAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231233');

      const secondAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231231');

      expect(get(firstAddressName)).toBeUndefined();
      expect(get(secondAddressName)).toBeUndefined();

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).toHaveBeenCalledOnce();

      expect(get(firstAddressName)).toBe('test_name');
      expect(get(secondAddressName)).toBe('test1.eth');
    });

    it('should use cached value if addresses names were fetched before', async () => {
      const firstAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231233');

      const secondAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231231');

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).not.toHaveBeenCalled();

      expect(get(firstAddressName)).toBe('test_name');
      expect(get(secondAddressName)).toBe('test1.eth');
    });

    it('should not match API result with null blockchain against a valid chain key', async () => {
      store.resetAddressesNames();

      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        enableAliasNames: true,
      });

      const address = '0xAA00000000000000000000000000000000000001';

      // API returns entry with null blockchain (multi-chain address)
      vi.mocked(api.getAddressesNames).mockResolvedValue([
        { address, blockchain: null, name: 'multi_chain_name' },
      ]);

      const addressName = store.addressNameSelector(address, Blockchain.ETH);

      // Initially undefined (pending)
      expect(get(addressName)).toBeUndefined();

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).toHaveBeenCalledOnce();

      // null blockchain should NOT match the ETH key, so name stays undefined
      expect(get(addressName)).toBeUndefined();
    });

    it('should match API result when blockchain matches the queried chain', async () => {
      store.resetAddressesNames();

      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        enableAliasNames: true,
      });

      const address = '0xBB00000000000000000000000000000000000002';

      // API returns entry with matching blockchain
      vi.mocked(api.getAddressesNames).mockResolvedValue([
        { address, blockchain: Blockchain.ETH, name: 'eth_name' },
      ]);

      const addressName = store.addressNameSelector(address, Blockchain.ETH);

      // Force computed evaluation to trigger resolve/queue before advancing timers
      expect(get(addressName)).toBeUndefined();

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(get(addressName)).toBe('eth_name');
    });

    it('should handle enableAliasNames when false', async () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        enableAliasNames: false,
      });

      const firstAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231233');

      const secondAddressName = store.addressNameSelector('0x4585FE77225b41b697C938B01232131231231231');

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).not.toHaveBeenCalled();

      expect(get(firstAddressName)).toBeUndefined();
      expect(get(secondAddressName)).toBeUndefined();
    });
  });
});
