import { useEthNamesApi } from '@/services/balances/ethereum-names';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { FrontendSettings } from '@/types/frontend-settings';

vi.mock('@/services/balances/ethereum-names', () => ({
  useEthNamesApi: vi.fn().mockReturnValue({
    getEnsNamesTask: vi.fn().mockResolvedValue(1),
    getEnsNames: vi.fn().mockResolvedValue({}),
    getEthAddressBook: vi.fn().mockResolvedValue([]),
    addEthAddressBook: vi.fn().mockResolvedValue(true),
    updateEthAddressBook: vi.fn().mockResolvedValue(true),
    deleteEthAddressBook: vi.fn().mockResolvedValue(true),
    getEthNames: vi.fn().mockResolvedValue({})
  })
}));

vi.mock('@/store/tasks', () => ({
  useTasks: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({})
  })
}));

describe('store::balances/ethereum-names', () => {
  setActivePinia(createPinia());
  const store: ReturnType<typeof useEthNamesStore> = useEthNamesStore();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchEnsNames', () => {
    const addresses = ['0x4585FE77225b41b697C938B01232131231231233'];

    test('no addresses', async () => {
      await store.fetchEnsNames([]);
      expect(useEthNamesApi().getEnsNames).not.toHaveBeenCalled();
    });

    test('with addresses, forceUpdate=false', async () => {
      await store.fetchEnsNames(addresses, false);

      expect(useEthNamesApi().getEnsNames).toHaveBeenCalledWith(addresses);
      expect(useEthNamesApi().getEthNames).toHaveBeenCalledOnce();
    });

    test('with same addresses, forceUpdate=false', async () => {
      await store.fetchEnsNames(addresses, false);

      expect(useEthNamesApi().getEnsNames).not.toHaveBeenCalledWith(addresses);
      expect(useEthNamesApi().getEthNames).not.toHaveBeenCalledOnce();
    });

    test('with same addresses, forceUpdate=true', async () => {
      await store.fetchEnsNames(addresses, true);

      expect(useEthNamesApi().getEnsNamesTask).toHaveBeenCalledWith(addresses);
      expect(useEthNamesApi().getEthNames).toHaveBeenCalledOnce();
    });

    test('filter invalid addresses, forceUpdate=true', async () => {
      await store.fetchEnsNames([...addresses, '0xinvalid'], true);

      expect(useEthNamesApi().getEnsNamesTask).toHaveBeenCalledWith(addresses);
      expect(useEthNamesApi().getEthNames).toHaveBeenCalledOnce();
    });
  });

  describe('fetchEthAddressBook', () => {
    const addresses = ['0x4585FE77225b41b697C938B01232131231231233'];
    const addressesWithEns = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        name: 'test.eth'
      }
    ];

    test('location=global', async () => {
      const { ethAddressBook } = storeToRefs(store);

      vi.mocked(useEthNamesApi().getEthAddressBook).mockResolvedValue(
        addressesWithEns
      );

      await store.fetchEthAddressBook('global', addresses);

      expect(useEthNamesApi().getEthAddressBook).toHaveBeenCalledWith(
        'global',
        addresses
      );

      expect(get(ethAddressBook).global).toEqual(addressesWithEns);
    });

    test('location=private', async () => {
      const { ethAddressBook } = storeToRefs(store);

      vi.mocked(useEthNamesApi().getEthAddressBook).mockResolvedValue(
        addressesWithEns
      );

      await store.fetchEthAddressBook('private', addresses);

      expect(useEthNamesApi().getEthAddressBook).toHaveBeenCalledWith(
        'private',
        addresses
      );

      expect(get(ethAddressBook).private).toEqual(addressesWithEns);
    });
  });

  describe('addEthAddressBook', () => {
    const entries = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        name: 'test_name'
      }
    ];

    test('default', async () => {
      await store.addEthAddressBook('global', entries);

      expect(useEthNamesApi().addEthAddressBook).toHaveBeenCalledWith(
        'global',
        entries
      );

      await store.addEthAddressBook('private', entries);

      expect(useEthNamesApi().addEthAddressBook).toHaveBeenCalledWith(
        'private',
        entries
      );
    });
  });

  describe('updateEthAddressBook', () => {
    const entries = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        name: 'test_name'
      }
    ];

    test('default', async () => {
      await store.updateEthAddressBook('global', entries);

      expect(useEthNamesApi().updateEthAddressBook).toHaveBeenCalledWith(
        'global',
        entries
      );

      await store.updateEthAddressBook('private', entries);

      expect(useEthNamesApi().updateEthAddressBook).toHaveBeenCalledWith(
        'private',
        entries
      );
    });
  });

  describe('deleteEthAddressBook', () => {
    const addresses = ['0x4585FE77225b41b697C938B01232131231231233'];

    test('default', async () => {
      await store.deleteEthAddressBook('global', addresses);

      expect(useEthNamesApi().deleteEthAddressBook).toHaveBeenCalledWith(
        'global',
        addresses
      );

      await store.deleteEthAddressBook('private', addresses);

      expect(useEthNamesApi().deleteEthAddressBook).toHaveBeenCalledWith(
        'private',
        addresses
      );
    });
  });

  describe('fetchEthNames', () => {
    const addressesWithEthNames = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        name: 'test_name'
      }
    ];

    const addresses = ['0x4585FE77225b41b697C938B01232131231231231'];
    const addressesWithEns = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231231',
        name: 'test1.eth'
      }
    ];

    const mockedResult = {
      '0x4585FE77225b41b697C938B01232131231231233': 'test_name',
      '0x4585FE77225b41b697C938B01232131231231231': 'test1.eth'
    };

    test('default', async () => {
      vi.mocked(useEthNamesApi().getEthAddressBook).mockResolvedValue(
        addressesWithEns
      );
      vi.mocked(useEthNamesApi().getEthNames).mockResolvedValue(mockedResult);

      await store.updateEthAddressBook('global', addressesWithEthNames);
      await store.updateEthAddressBook('private', addressesWithEthNames);

      await store.fetchEnsNames(addresses);

      expect(useEthNamesApi().getEthNames).toHaveBeenCalledWith([
        '0x4585FE77225b41b697C938B01232131231231231',
        '0x4585FE77225b41b697C938B01232131231231233'
      ]);

      const { ethNames } = storeToRefs(store);
      expect(get(ethNames)).toMatchObject(mockedResult);
    });
  });

  describe('ethNameSelector', () => {
    test('enableEthNames=true', () => {
      expect(
        get(store.ethNameSelector('0x4585FE77225b41b697C938B01232131231231233'))
      ).toEqual('test_name');

      expect(
        get(store.ethNameSelector('0x4585FE77225b41b697C938B01232131231231231'))
      ).toEqual('test1.eth');
    });

    test('enableEthNames=false', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        enableEthNames: false
      });

      expect(
        get(store.ethNameSelector('0x4585FE77225b41b697C938B01232131231231233'))
      ).toEqual(null);

      expect(
        get(store.ethNameSelector('0x4585FE77225b41b697C938B01232131231231231'))
      ).toEqual(null);
    });
  });
});
