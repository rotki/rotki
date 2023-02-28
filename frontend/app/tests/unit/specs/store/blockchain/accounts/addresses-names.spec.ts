import { Blockchain } from '@rotki/common/lib/blockchain';
import { FrontendSettings } from '@/types/frontend-settings';
import { useAddressesNamesApi } from '@/composables/api/blockchain/addresses-names';

vi.mock('@/composables/api/blockchain/addresses-names', () => ({
  useAddressesNamesApi: vi.fn().mockReturnValue({
    getEnsNamesTask: vi.fn().mockResolvedValue(1),
    getEnsNames: vi.fn().mockResolvedValue([]),
    getAddressBook: vi.fn().mockResolvedValue([]),
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
    store = useAddressesNamesStore();
    api = useAddressesNamesApi();
    vi.clearAllMocks();
  });

  describe('fetchEnsNames', () => {
    const addresses = ['0x4585FE77225b41b697C938B01232131231231233'];

    test('no addresses', async () => {
      await store.fetchEnsNames([]);
      expect(api.getEnsNames).not.toHaveBeenCalled();
    });

    test('with addresses, forceUpdate=false', async () => {
      await store.fetchEnsNames(addresses, false);

      expect(api.getEnsNames).toHaveBeenCalledWith(addresses);
      expect(api.getAddressesNames).toHaveBeenCalledOnce();
    });

    test('with same addresses, forceUpdate=true', async () => {
      await store.fetchEnsNames(addresses, true);

      expect(api.getEnsNamesTask).toHaveBeenCalledWith(addresses);
      expect(api.getAddressesNames).toHaveBeenCalledOnce();
    });

    test('filter invalid addresses, forceUpdate=true', async () => {
      await store.fetchEnsNames([...addresses, '0xinvalid'], true);

      expect(api.getEnsNamesTask).toHaveBeenCalledWith(addresses);
      expect(api.getAddressesNames).toHaveBeenCalledOnce();
    });
  });

  describe('fetchAddressBook', () => {
    const addresses = ['0x4585FE77225b41b697C938B01232131231231233'];
    const addressesWithEns = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        name: 'test.eth',
        blockchain: Blockchain.ETH
      }
    ];

    test('location=global', async () => {
      const { addressBookEntries } = storeToRefs(store);

      vi.mocked(api.getAddressBook).mockResolvedValue(addressesWithEns);

      await store.fetchAddressBook('global', addresses);

      expect(api.getAddressBook).toHaveBeenCalledWith('global', addresses);

      expect(get(addressBookEntries).global).toEqual(addressesWithEns);
    });

    test('location=private', async () => {
      const { addressBookEntries } = storeToRefs(store);

      vi.mocked(api.getAddressBook).mockResolvedValue(addressesWithEns);

      await store.fetchAddressBook('private', addresses);

      expect(api.getAddressBook).toHaveBeenCalledWith('private', addresses);

      expect(get(addressBookEntries).private).toEqual(addressesWithEns);
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

  describe('fetchAddressesNames', () => {
    const addressesWithEthNames = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        name: 'test_name',
        blockchain: Blockchain.ETH
      }
    ];

    const addresses = ['0x4585FE77225b41b697C938B01232131231231231'];
    const addressesWithEns = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231231',
        name: 'test1.eth',
        blockchain: Blockchain.ETH
      }
    ];

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

    test('default', async () => {
      vi.mocked(api.getAddressBook).mockResolvedValue(addressesWithEns);
      vi.mocked(api.getAddressesNames).mockResolvedValue(mockedResult);

      await store.updateAddressBook('global', addressesWithEthNames);
      await store.updateAddressBook('private', addressesWithEthNames);

      await store.fetchEnsNames(addresses);

      expect(api.getAddressesNames).toHaveBeenCalledWith([
        {
          address: '0x4585FE77225b41b697C938B01232131231231231',
          blockchain: Blockchain.ETH
        },
        {
          address: '0x4585FE77225b41b697C938B01232131231231233',
          blockchain: Blockchain.ETH
        }
      ]);

      const { addressesNames } = storeToRefs(store);
      expect(get(addressesNames)).toMatchObject(mockedResult);
    });
  });

  describe('addressNameSelector', () => {
    test('enableAliasNames=true', () => {
      expect(
        get(
          store.addressNameSelector(
            '0x4585FE77225b41b697C938B01232131231231233'
          )
        )
      ).toEqual('test_name');

      expect(
        get(
          store.addressNameSelector(
            '0x4585FE77225b41b697C938B01232131231231231'
          )
        )
      ).toEqual('test1.eth');
    });

    test('enableAliasNames=false', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        enableAliasNames: false
      });

      expect(
        get(
          store.addressNameSelector(
            '0x4585FE77225b41b697C938B01232131231231233'
          )
        )
      ).toEqual(null);

      expect(
        get(
          store.addressNameSelector(
            '0x4585FE77225b41b697C938B01232131231231231'
          )
        )
      ).toEqual(null);
    });
  });
});
