import { Blockchain } from '@rotki/common/lib/blockchain';
import flushPromises from 'flush-promises';
import {
  type AddressBookEntry,
  type AddressBookSimplePayload
} from '@/types/eth-names';
import { type Collection } from '@/types/collection';
import { FrontendSettings } from '@/types/settings/frontend-settings';

vi.mock('@/composables/api/blockchain/addresses-names', () => ({
  useAddressesNamesApi: vi.fn().mockReturnValue({
    getEnsNamesTask: vi.fn().mockResolvedValue(1),
    getEnsNames: vi.fn().mockResolvedValue([]),
    fetchAddressBook: vi.fn().mockResolvedValue(defaultCollectionState()),
    addAddressBook: vi.fn().mockResolvedValue(true),
    updateAddressBook: vi.fn().mockResolvedValue(true),
    deleteAddressBook: vi.fn().mockResolvedValue(true),
    getAddressesNames: vi.fn().mockResolvedValue([])
  })
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({})
  })
}));

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    isEvm: vi.fn().mockReturnValue(ref(true))
  })
}));

describe('store::blockchain/accounts/addresses-names', () => {
  setActivePinia(createPinia());
  let store: ReturnType<typeof useAddressesNamesStore>;
  let api: ReturnType<typeof useAddressesNamesApi>;

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
        blockchain: Blockchain.ETH
      }
    ];

    test('no addresses', async () => {
      await store.fetchEnsNames([]);
      expect(api.getEnsNames).not.toHaveBeenCalled();
    });

    test('with addresses, forceUpdate=false', async () => {
      await store.fetchEnsNames(addresses, false);

      expect(api.getEnsNames).toHaveBeenCalledWith(
        addresses.map(({ address }) => address)
      );
    });

    test('with same addresses, forceUpdate=true', async () => {
      await store.fetchEnsNames(addresses, true);

      expect(api.getEnsNamesTask).toHaveBeenCalledWith(
        addresses.map(({ address }) => address)
      );
    });

    test('filter invalid addresses, forceUpdate=true', async () => {
      await store.fetchEnsNames(
        [...addresses, { address: '0xinvalid', blockchain: Blockchain.ETH }],
        true
      );

      expect(api.getEnsNamesTask).toHaveBeenCalledWith(
        addresses.map(({ address }) => address)
      );
    });
  });

  describe('fetchAddressBook', () => {
    const address = ['0x4585FE77225b41b697C938B01232131231231233'];
    const payload = {
      address,
      limit: 10,
      offset: 0
    };
    const addressesWithEns: AddressBookEntry[] = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        name: 'test.eth',
        blockchain: Blockchain.ETH
      }
    ];

    const collection: Collection<AddressBookEntry> = {
      data: addressesWithEns,
      limit: 0,
      found: 1,
      total: 1
    };

    test('location=global', async () => {
      vi.mocked(api.fetchAddressBook).mockResolvedValue(collection);

      const result = await store.getAddressBook('global', payload);

      expect(api.fetchAddressBook).toHaveBeenCalledWith('global', payload);

      expect(result).toEqual(collection);
    });

    test('location=global', async () => {
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
        blockchain: Blockchain.ETH
      }
    ];

    test('default', async () => {
      await store.addAddressBook('global', entries);

      expect(api.addAddressBook).toHaveBeenCalledWith('global', entries);

      await store.addAddressBook('private', entries);

      expect(api.addAddressBook).toHaveBeenCalledWith('private', entries);
    });
  });

  describe('updateAddressBook', () => {
    const entries = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        name: 'test_name',
        blockchain: Blockchain.ETH
      }
    ];

    test('default', async () => {
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
        blockchain: Blockchain.ETH
      }
    ];

    test('default', async () => {
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
        name: 'test_name'
      },
      {
        address: '0x4585FE77225b41b697C938B01232131231231231',
        blockchain: Blockchain.ETH,
        name: 'test1.eth'
      }
    ];

    test('enableAliasNames=true', async () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        enableAliasNames: true
      });

      vi.mocked(api.getAddressesNames).mockResolvedValue(mockedResult);
      const firstAddressName = store.addressNameSelector(
        '0x4585FE77225b41b697C938B01232131231231233'
      );

      const secondAddressName = store.addressNameSelector(
        '0x4585FE77225b41b697C938B01232131231231231'
      );

      expect(get(firstAddressName)).toEqual(null);
      expect(get(secondAddressName)).toEqual(null);

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).toHaveBeenCalledOnce();

      expect(get(firstAddressName)).toEqual('test_name');
      expect(get(secondAddressName)).toEqual('test1.eth');
    });

    test('use the value from cache if addresses names has been fetched before', async () => {
      const firstAddressName = store.addressNameSelector(
        '0x4585FE77225b41b697C938B01232131231231233'
      );

      const secondAddressName = store.addressNameSelector(
        '0x4585FE77225b41b697C938B01232131231231231'
      );

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).not.toHaveBeenCalled();

      expect(get(firstAddressName)).toEqual('test_name');
      expect(get(secondAddressName)).toEqual('test1.eth');
    });

    test('enableAliasNames=false', async () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        enableAliasNames: false
      });

      const firstAddressName = store.addressNameSelector(
        '0x4585FE77225b41b697C938B01232131231231233'
      );

      const secondAddressName = store.addressNameSelector(
        '0x4585FE77225b41b697C938B01232131231231231'
      );

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).not.toHaveBeenCalled();

      expect(get(firstAddressName)).toEqual(null);
      expect(get(secondAddressName)).toEqual(null);
    });
  });
});
