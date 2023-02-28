import { Blockchain } from '@rotki/common/lib/blockchain';
import { Module } from '@/types/modules';
import { type GeneralAccountData } from '@/types/blockchain/accounts';
import { setModules } from '../../../../utils/modules';

vi.mock('@/composables/api/blockchain/accounts', () => ({
  useBlockchainAccountsApi: vi.fn().mockReturnValue({
    getEth2Validators: vi.fn().mockResolvedValue({
      entries: [],
      entriesFound: 0,
      entriesLimit: 0
    }),
    addEth2Validator: vi.fn().mockResolvedValue(1),
    editEth2Validator: vi.fn().mockResolvedValue(true),
    deleteEth2Validators: vi.fn().mockResolvedValue(true)
  })
}));

vi.mock('@/store/notifications/index', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    notify: vi.fn().mockReturnValue({})
  })
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({})
  })
}));

describe('store::blockchain/accounts/eth', () => {
  setActivePinia(createPinia());
  let store: ReturnType<typeof useEthAccountsStore>;
  let api: ReturnType<typeof useBlockchainAccountsApi>;

  const publicKey =
    '0x8472eb896af6de1e3d614e9b8fead626120291d5067edf15961c3e7385a0299d09f7f94eb6bbf96e904e7caf390ffd2f';

  const payload = {
    validatorIndex: '135446',
    publicKey,
    ownershipPercentage: '100'
  };

  const eth2ValidatorsData = {
    entries: [
      {
        ...payload,
        validatorIndex: parseInt(payload.validatorIndex)
      }
    ],
    entriesFound: 1,
    entriesLimit: 1
  };

  beforeEach(() => {
    store = useEthAccountsStore();
    api = useBlockchainAccountsApi();

    vi.clearAllMocks();
  });

  describe('fetchEth2Validators', () => {
    test('module is not enabled', async () => {
      await store.fetchEth2Validators();

      expect(api.getEth2Validators).not.toHaveBeenCalled();
    });

    test('success', async () => {
      setModules([Module.ETH2]);

      await store.fetchEth2Validators();

      expect(api.getEth2Validators).toHaveBeenCalled();

      expect(useNotificationsStore().notify).not.toHaveBeenCalled();
    });

    test('error', async () => {
      const { getEth2Validators } = useBlockchainAccountsApi();

      vi.mocked(getEth2Validators).mockRejectedValue(new Error('failed'));

      await store.fetchEth2Validators();

      expect(getEth2Validators).toHaveBeenCalled();

      expect(useNotificationsStore().notify).toHaveBeenCalled();
    });
  });

  describe('addEth2Validator', () => {
    test('module is not enabled', async () => {
      setModules([]);

      await store.addEth2Validator(payload);

      expect(api.addEth2Validator).not.toHaveBeenCalled();
    });

    test('success', async () => {
      setModules([Module.ETH2]);

      const { addEth2Validator } = useBlockchainAccountsApi();

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: true,
        meta: { title: '' }
      });

      const result = await store.addEth2Validator(payload);

      expect(addEth2Validator).toHaveBeenCalledWith(payload);

      expect(result.success).toBeTruthy();
    });

    test('error', async () => {
      const errorMessage = 'failed';
      const { addEth2Validator } = useBlockchainAccountsApi();

      vi.mocked(addEth2Validator).mockRejectedValue(new Error(errorMessage));

      const result = await store.addEth2Validator(payload);

      expect(addEth2Validator).toHaveBeenCalledWith(payload);

      expect(result).toEqual({
        success: false,
        message: errorMessage
      });
    });
  });

  describe('editEth2Validator', () => {
    test('module is not enabled', async () => {
      setModules([]);

      await store.editEth2Validator(payload);

      expect(api.editEth2Validator).not.toHaveBeenCalled();
    });

    test('success', async () => {
      setModules([Module.ETH2]);

      const { editEth2Validator } = api;

      const result = await store.editEth2Validator(payload);

      expect(editEth2Validator).toHaveBeenCalledWith(payload);

      expect(result.success).toBeTruthy();
    });

    test('error', async () => {
      const errorMessage = 'failed';
      const { editEth2Validator } = api;

      vi.mocked(editEth2Validator).mockRejectedValue(new Error(errorMessage));

      const result = await store.editEth2Validator(payload);

      expect(editEth2Validator).toHaveBeenCalledWith(payload);

      expect(result).toEqual({
        success: false,
        message: errorMessage
      });
    });
  });

  describe('deleteEth2Validator', () => {
    test('success', async () => {
      const { eth2Validators } = storeToRefs(store);
      set(eth2Validators, eth2ValidatorsData);

      const { deleteEth2Validators } = api;

      const success = await store.deleteEth2Validators([publicKey]);

      expect(deleteEth2Validators).toHaveBeenCalledWith([
        eth2ValidatorsData.entries[0]
      ]);

      expect(success).toBeTruthy();
    });

    test('error', async () => {
      const { eth2Validators } = storeToRefs(store);
      set(eth2Validators, eth2ValidatorsData);

      const errorMessage = 'failed to delete eth2 validators';
      const { deleteEth2Validators } = api;

      vi.mocked(deleteEth2Validators).mockRejectedValue(
        new Error(errorMessage)
      );

      const success = await store.deleteEth2Validators([publicKey]);

      expect(deleteEth2Validators).toHaveBeenCalledWith([
        eth2ValidatorsData.entries[0]
      ]);

      expect(success).toBeFalsy();

      const messageStore = useMessageStore();
      expect(messageStore.message.description).toMatch(errorMessage);
    });
  });

  describe('getEth2Account', () => {
    test('default', () => {
      const result = get(store.getEth2Account(publicKey));

      expect(result).toEqual({
        address: payload.publicKey,
        label: payload.validatorIndex,
        tags: [],
        chain: Blockchain.ETH2
      });
    });

    test('not found', () => {
      const result = get(store.getEth2Account('wrong_public_key'));

      expect(result).toEqual(undefined);
    });
  });

  const address = '0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea';
  const tag = 'tag_1';

  test('update ETH account', () => {
    const { eth } = storeToRefs(store);
    set(eth, []);

    expect(get(eth)).toEqual([]);
    const accounts: GeneralAccountData[] = [
      {
        address,
        label: 'test eth',
        tags: [tag]
      }
    ];

    store.updateEth(accounts);

    expect(get(eth)).toEqual(accounts);
  });

  test('removeTag', () => {
    const { eth, ethAddresses } = storeToRefs(store);

    const newData: GeneralAccountData = {
      address,
      label: 'test eth',
      tags: []
    };

    store.removeTag(tag);

    expect(get(eth)).toEqual([newData]);
    expect(get(ethAddresses)).toEqual([address]);
  });
});
