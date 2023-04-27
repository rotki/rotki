import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  type AccountPayload,
  type BasicBlockchainAccountPayload,
  type BlockchainAccountPayload
} from '@/types/blockchain/accounts';

vi.mock('@/composables/api/blockchain/accounts', () => ({
  useBlockchainAccountsApi: vi.fn().mockReturnValue({
    addBlockchainAccount: vi.fn().mockResolvedValue(1),
    removeBlockchainAccount: vi.fn().mockResolvedValue(1),
    editBlockchainAccount: vi.fn().mockResolvedValue([]),
    editBtcAccount: vi.fn().mockResolvedValue({ standalone: [], xpubs: [] }),
    queryAccounts: vi.fn().mockResolvedValue([]),
    queryBtcAccounts: vi.fn().mockResolvedValue({ standalone: [], xpubs: [] }),
    getEth2Validators: vi.fn().mockResolvedValue([])
  })
}));

vi.mock('@/store/notifications/index', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    notify: vi.fn().mockReturnValue({})
  })
}));

vi.mock('@/store/blockchain/accounts/btc', () => ({
  useBtcAccountsStore: vi.fn().mockReturnValue({
    removeTag: vi.fn(),
    update: vi.fn()
  })
}));

vi.mock('@/store/blockchain/accounts/eth', () => ({
  useEthAccountsStore: vi.fn().mockReturnValue({
    removeTag: vi.fn(),
    updateEth: vi.fn(),
    fetchEth2Validators: vi.fn()
  })
}));

vi.mock('@/store/blockchain/accounts/chains', () => ({
  useChainsAccountsStore: vi.fn().mockReturnValue({
    removeTag: vi.fn(),
    updateEth: vi.fn(),
    update: vi.fn()
  })
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({})
  })
}));

describe('store::blockchain/accounts/index', () => {
  setActivePinia(createPinia());
  let store: ReturnType<typeof useBlockchainAccounts> = useBlockchainAccounts();
  let api: ReturnType<typeof useBlockchainAccountsApi> =
    useBlockchainAccountsApi();

  beforeEach(() => {
    store = useBlockchainAccounts();
    api = useBlockchainAccountsApi();
    vi.clearAllMocks();
  });

  describe('addAccount', () => {
    test('default', async () => {
      const blockchain = Blockchain.ETH;
      const payload: AccountPayload = {
        address: '0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea',
        label: 'ETH test address',
        tags: null,
        xpub: undefined
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: [payload.address],
        meta: { title: '' }
      });

      const returnValue = await store.addAccount(blockchain, payload);

      expect(api.addBlockchainAccount).toHaveBeenCalledWith({
        blockchain,
        ...payload
      });

      expect(returnValue).toEqual(payload.address);
    });
  });

  describe('editAccount', () => {
    test('for BTC account', async () => {
      const payload: BlockchainAccountPayload = {
        blockchain: Blockchain.BTC,
        address: '3PFo18vaPMSXFTt6zUDGk3UoPjD56QLXjh',
        tags: null
      };

      await store.editAccount(payload);

      expect(api.editBtcAccount).toHaveBeenCalledWith(payload);
    });

    test('for ETH account', async () => {
      const payload: BlockchainAccountPayload = {
        blockchain: Blockchain.ETH,
        address: '0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea',
        tags: null
      };

      await store.editAccount(payload);

      expect(api.editBlockchainAccount).toHaveBeenCalledWith(payload);
    });
  });

  describe('removeAccount', () => {
    test('success', async () => {
      const payload: BasicBlockchainAccountPayload = {
        blockchain: Blockchain.ETH,
        accounts: ['0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea']
      };

      await store.removeAccount(payload);

      expect(api.removeBlockchainAccount).toHaveBeenCalledWith(
        payload.blockchain,
        payload.accounts
      );

      expect(useNotificationsStore().notify).not.toHaveBeenCalled();
    });

    test('error', async () => {
      const payload: BasicBlockchainAccountPayload = {
        blockchain: Blockchain.ETH,
        accounts: ['0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea']
      };

      vi.mocked(useTaskStore().awaitTask).mockRejectedValue(
        new Error('failed')
      );

      await store.removeAccount(payload);

      expect(api.removeBlockchainAccount).toHaveBeenCalledWith(
        payload.blockchain,
        payload.accounts
      );

      expect(useNotificationsStore().notify).toHaveBeenCalled();
    });
  });

  describe('fetch', () => {
    test('fetch BTC chain', async () => {
      await store.fetch(Blockchain.BTC);
      expect(useBlockchainAccountsApi().queryBtcAccounts).toHaveBeenCalledWith(
        Blockchain.BTC
      );

      await store.fetch(Blockchain.BCH);
      expect(useBlockchainAccountsApi().queryBtcAccounts).toHaveBeenCalledWith(
        Blockchain.BCH
      );
    });

    test('fetch ETH2 validators', async () => {
      await store.fetch(Blockchain.ETH2);
      expect(useEthAccountsStore().fetchEth2Validators).toHaveBeenCalledOnce();
    });

    test('fetch rest chains / ETH', async () => {
      await store.fetch(Blockchain.ETH);
      expect(useBlockchainAccountsApi().queryAccounts).toHaveBeenCalledWith(
        Blockchain.ETH
      );

      await store.fetch(Blockchain.KSM);
      expect(useBlockchainAccountsApi().queryAccounts).toHaveBeenCalledWith(
        Blockchain.KSM
      );

      await store.fetch(Blockchain.DOT);
      expect(useBlockchainAccountsApi().queryAccounts).toHaveBeenCalledWith(
        Blockchain.DOT
      );

      await store.fetch(Blockchain.AVAX);
      expect(useBlockchainAccountsApi().queryAccounts).toHaveBeenCalledWith(
        Blockchain.AVAX
      );

      await store.fetch(Blockchain.OPTIMISM);
      expect(useBlockchainAccountsApi().queryAccounts).toHaveBeenCalledWith(
        Blockchain.OPTIMISM
      );
    });
  });

  describe('removeTag', () => {
    test('default', () => {
      const tag = 'tag_1';
      store.removeTag(tag);

      expect(useBtcAccountsStore().removeTag).toHaveBeenCalledWith(tag);
      expect(useEthAccountsStore().removeTag).toHaveBeenCalledWith(tag);
      expect(useChainsAccountsStore().removeTag).toHaveBeenCalledWith(tag);
    });
  });
});
