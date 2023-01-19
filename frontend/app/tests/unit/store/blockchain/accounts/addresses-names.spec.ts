import { Blockchain } from '@rotki/common/lib/blockchain';
import { useAddressesNamesApi } from '@/services/blockchain/addresses-names';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { FrontendSettings } from '@/types/frontend-settings';

vi.mock('@/services/blockchain/addresses-names', () => ({
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
  useTasks: vi.fn().mockReturnValue({
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
  const store: ReturnType<typeof useAddressesNamesStore> =
    useAddressesNamesStore();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchEnsNames', () => {
    const addresses = ['0x4585FE77225b41b697C938B01232131231231233'];

    test('no addresses', async () => {
      await store.fetchEnsNames([]);
      expect(useAddressesNamesApi().getEnsNames).not.toHaveBeenCalled();
    });

    test('with addresses, forceUpdate=false', async () => {
      await store.fetchEnsNames(addresses, false);

      expect(useAddressesNamesApi().getEnsNames).toHaveBeenCalledWith(
        addresses
      );
      expect(useAddressesNamesApi().getAddressesNames).toHaveBeenCalledOnce();
    });

    test('with same addresses, forceUpdate=true', async () => {
      await store.fetchEnsNames(addresses, true);

      expect(useAddressesNamesApi().getEnsNamesTask).toHaveBeenCalledWith(
        addresses
      );
      expect(useAddressesNamesApi().getAddressesNames).toHaveBeenCalledOnce();
    });

    test('filter invalid addresses, forceUpdate=true', async () => {
      await store.fetchEnsNames([...addresses, '0xinvalid'], true);

      expect(useAddressesNamesApi().getEnsNamesTask).toHaveBeenCalledWith(
        addresses
      );
      expect(useAddressesNamesApi().getAddressesNames).toHaveBeenCalledOnce();
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

      vi.mocked(useAddressesNamesApi().getAddressBook).mockResolvedValue(
        addressesWithEns
      );

      await store.fetchAddressBook('global', addresses);

      expect(useAddressesNamesApi().getAddressBook).toHaveBeenCalledWith(
        'global',
        addresses
      );

      expect(get(addressBookEntries).global).toEqual(addressesWithEns);
    });

    test('location=private', async () => {
      const { addressBookEntries } = storeToRefs(store);

      vi.mocked(useAddressesNamesApi().getAddressBook).mockResolvedValue(
        addressesWithEns
      );

      await store.fetchAddressBook('private', addresses);

      expect(useAddressesNamesApi().getAddressBook).toHaveBeenCalledWith(
        'private',
        addresses
      );

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

      expect(useAddressesNamesApi().addAddressBook).toHaveBeenCalledWith(
        'global',
        entries
      );

      await store.addAddressBook('private', entries);

      expect(useAddressesNamesApi().addAddressBook).toHaveBeenCalledWith(
        'private',
        entries
      );
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

      expect(useAddressesNamesApi().updateAddressBook).toHaveBeenCalledWith(
        'global',
        entries
      );

      await store.updateAddressBook('private', entries);

      expect(useAddressesNamesApi().updateAddressBook).toHaveBeenCalledWith(
        'private',
        entries
      );
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

      expect(useAddressesNamesApi().deleteAddressBook).toHaveBeenCalledWith(
        'global',
        addresses
      );

      await store.deleteAddressBook('private', addresses);

      expect(useAddressesNamesApi().deleteAddressBook).toHaveBeenCalledWith(
        'private',
        addresses
      );
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
      vi.mocked(useAddressesNamesApi().getAddressBook).mockResolvedValue(
        addressesWithEns
      );
      vi.mocked(useAddressesNamesApi().getAddressesNames).mockResolvedValue(
        mockedResult
      );

      await store.updateAddressBook('global', addressesWithEthNames);
      await store.updateAddressBook('private', addressesWithEthNames);

      await store.fetchEnsNames(addresses);

      expect(useAddressesNamesApi().getAddressesNames).toHaveBeenCalledWith([
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
