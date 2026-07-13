import type { TransactionParams } from './types';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { WALLET_MODES } from './constants';

const txParams: TransactionParams = { amount: '1', chain: 'ethereum', native: true, to: '0xto' };

// Stable mock fns + a per-test state bag. Because the store re-imports its
// dependencies through `vi.resetModules()` and lazy dynamic imports, the mock
// factories below return functions that read `mocks.state` at call time, so
// each fresh import still sees the fakes wired up in beforeEach.
const mocks = vi.hoisted((): {
  handleTransactionError: ReturnType<typeof vi.fn>;
  prepareTransactionPayload: ReturnType<typeof vi.fn>;
  state: Record<string, any>;
  validateTransactionRequirements: ReturnType<typeof vi.fn>;
} => ({
  handleTransactionError: vi.fn(),
  prepareTransactionPayload: vi.fn(),
  state: {},
  validateTransactionRequirements: vi.fn(),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

vi.mock('@/modules/wallet/viem-client', () => ({
  getAddress: vi.fn((address: string) => address),
  isHex: vi.fn(() => true),
}));

vi.mock('./transaction-helpers', () => ({
  handleTransactionError: mocks.handleTransactionError,
  prepareTransactionPayload: mocks.prepareTransactionPayload,
  validateTransactionRequirements: mocks.validateTransactionRequirements,
}));

type Fake = Record<string, any>;

vi.mock('./bridge/use-wallet-proxy', () => ({ useWalletProxy: (): Fake => mocks.state.walletProxy }));
vi.mock('./providers/use-unified-providers', () => ({ useUnifiedProviders: (): Fake => mocks.state.unifiedProviders }));
vi.mock('./use-transaction-manager', () => ({ useTransactionManager: (): Fake => mocks.state.transactionManager }));
vi.mock('./send/use-trade-api', () => ({ useTradeApi: (): Fake => mocks.state.tradeApi }));
vi.mock('./use-wallet-connect', () => ({ useWalletConnect: (): Fake => mocks.state.walletConnect }));
vi.mock('./bridge/use-injected-wallet', () => ({ useInjectedWallet: (): Fake => mocks.state.injectedWallet }));
vi.mock('@/modules/shell/app/use-electron-interop', () => ({ useInterop: (): Fake => ({ isPackaged: mocks.state.isPackaged }) }));
vi.mock('@/modules/wallet/use-wallet-helper', () => ({ useWalletHelper: (): Fake => mocks.state.walletHelper }));
vi.mock('@/modules/core/common/use-supported-chains', () => ({ useSupportedChains: (): Fake => mocks.state.supportedChains }));

function makeInjectedWallet(): Record<string, any> {
  return {
    connected: ref(false),
    connectedAddress: ref<string>(),
    connectedChainId: ref<number>(),
    connectToSelectedProvider: vi.fn(async () => {}),
    disconnect: vi.fn(async () => {}),
    getWalletClient: vi.fn(() => ({
      getBalance: vi.fn(async () => 5n),
      getGasPrice: vi.fn(async () => 2n),
      sendTransaction: vi.fn(async () => '0xhash'),
    })),
    isConnecting: ref(false),
    switchNetwork: vi.fn(async () => {}),
  };
}

function makeWalletConnect(): Record<string, any> {
  return {
    checkWalletConnection: vi.fn(async () => {}),
    connect: vi.fn(async () => {}),
    connected: ref(false),
    connectedAddress: ref<string>(),
    connectedChainId: ref<number>(),
    disconnect: vi.fn(async () => {}),
    getWalletClient: vi.fn(() => ({ sendTransaction: vi.fn(async () => '0xwc') })),
    supportedChainIds: ref<string[]>([]),
    switchNetwork: vi.fn(async () => {}),
  };
}

async function getStore(): Promise<ReturnType<typeof import('./use-wallet-store').useWalletStore>> {
  const { useWalletStore } = await import('./use-wallet-store');
  return useWalletStore();
}

describe('modules/wallet/use-wallet-store', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    setActivePinia(createPinia());

    mocks.state = {
      injectedWallet: makeInjectedWallet(),
      isPackaged: ref<boolean>(false),
      supportedChains: { getEvmChainName: vi.fn(() => 'ethereum') },
      tradeApi: { prepareERC20Transfer: vi.fn(), prepareNativeTransfer: vi.fn() },
      transactionManager: {
        handleTransactionSuccess: vi.fn(async () => {}),
        recentTransactions: ref([]),
        updateTransactionStatus: vi.fn(),
      },
      unifiedProviders: {
        availableProviders: ref<{ info: { uuid: string } }[]>([]),
        checkIfSelectedProvider: vi.fn(async () => true),
        clearProvider: vi.fn(),
        detectProviders: vi.fn(async () => {}),
        selectProvider: vi.fn(async () => {}),
        showProviderSelection: ref<boolean>(false),
      },
      walletConnect: makeWalletConnect(),
      walletHelper: {
        getChainFromChainId: vi.fn((chainId: number) => `chain-${chainId}`),
        getChainIdFromNamespace: vi.fn((ns: string) => Number(ns.split(':').pop())),
      },
      walletProxy: { setupProxy: vi.fn(async () => {}) },
    };
  });

  const injected = (): Record<string, any> => mocks.state.injectedWallet;
  const providers = (): Record<string, any> => mocks.state.unifiedProviders;
  const walletConnect = (): Record<string, any> => mocks.state.walletConnect;

  it('should start in local-bridge mode and disconnected', async () => {
    const store = await getStore();
    expect(get(store.walletMode)).toBe(WALLET_MODES.LOCAL_BRIDGE);
    expect(get(store.connected)).toBe(false);
    expect(get(store.isWalletConnect)).toBe(false);
  });

  it('should reflect walletconnect mode in isWalletConnect', async () => {
    const store = await getStore();
    store.walletMode = WALLET_MODES.WALLET_CONNECT;
    await nextTick();
    expect(get(store.isWalletConnect)).toBe(true);
  });

  describe('connect (local bridge)', () => {
    it('should connect to the already-selected provider', async () => {
      providers().checkIfSelectedProvider.mockResolvedValue(true);
      const store = await getStore();
      await store.connect();

      expect(injected().connectToSelectedProvider).toHaveBeenCalledTimes(1);
      expect(providers().detectProviders).not.toHaveBeenCalled();
    });

    it('should auto-select the sole detected provider', async () => {
      providers().checkIfSelectedProvider.mockResolvedValue(false);
      set(providers().availableProviders, [{ info: { uuid: 'only-one' } }]);
      const store = await getStore();
      await store.connect();

      expect(providers().detectProviders).toHaveBeenCalledTimes(1);
      expect(providers().selectProvider).toHaveBeenCalledWith('only-one');
      expect(injected().connectToSelectedProvider).toHaveBeenCalledTimes(1);
    });

    it('should show the provider selection dialog when several are detected', async () => {
      providers().checkIfSelectedProvider.mockResolvedValue(false);
      set(providers().availableProviders, [{ info: { uuid: 'a' } }, { info: { uuid: 'b' } }]);
      const store = await getStore();
      await store.connect();

      expect(get(providers().showProviderSelection)).toBe(true);
      expect(providers().selectProvider).not.toHaveBeenCalled();
    });

    it('should throw when no providers are detected', async () => {
      providers().checkIfSelectedProvider.mockResolvedValue(false);
      set(providers().availableProviders, []);
      const store = await getStore();

      await expect(store.connect()).rejects.toThrow('No wallet providers detected');
    });

    it('should set up the proxy when running packaged', async () => {
      set(mocks.state.isPackaged, true);
      const store = await getStore();
      await store.connect();
      expect(mocks.state.walletProxy.setupProxy).toHaveBeenCalledTimes(1);
    });

    it('should not set up the proxy when not packaged', async () => {
      const store = await getStore();
      await store.connect();
      expect(mocks.state.walletProxy.setupProxy).not.toHaveBeenCalled();
    });
  });

  describe('connect (walletconnect)', () => {
    it('should delegate connection to the walletconnect backend', async () => {
      const store = await getStore();
      store.walletMode = WALLET_MODES.WALLET_CONNECT;
      await nextTick();

      await store.connect();
      expect(walletConnect().connect).toHaveBeenCalledTimes(1);
    });
  });

  describe('disconnect', () => {
    it('should disconnect the injected wallet and clear the provider in local bridge', async () => {
      const store = await getStore();
      await store.connect(); // initialise injected instance

      await store.disconnect();

      expect(injected().disconnect).toHaveBeenCalledTimes(1);
      expect(providers().clearProvider).toHaveBeenCalled();
      expect(get(store.connected)).toBe(false);
      expect(get(store.isDisconnecting)).toBe(false);
    });
  });

  describe('switchNetwork', () => {
    it('should delegate to the injected wallet in local bridge', async () => {
      const store = await getStore();
      await store.switchNetwork(10n);
      expect(injected().switchNetwork).toHaveBeenCalledWith(10n);
    });

    it('should delegate to walletconnect in walletconnect mode', async () => {
      const store = await getStore();
      store.walletMode = WALLET_MODES.WALLET_CONNECT;
      await nextTick();
      await store.switchNetwork(56n);
      expect(walletConnect().switchNetwork).toHaveBeenCalledWith(56n);
    });
  });

  describe('supportedChainsForConnectedAccount', () => {
    it('should list all supported chains in local bridge mode', async () => {
      const store = await getStore();
      expect(get(store.supportedChainsForConnectedAccount)).toEqual([
        'chain-1',
        'chain-8453',
        'chain-42161',
        'chain-10',
        'chain-56',
        'chain-100',
        'chain-137',
        'chain-534352',
      ]);
    });
  });

  describe('getGasFeeForChain', () => {
    it('should return zero when no address is connected', async () => {
      const store = await getStore();
      await store.connect();
      const result = await store.getGasFeeForChain();
      expect(result).toEqual({ gasFee: '0', maxAmount: '0' });
    });
  });

  describe('sendTransaction', () => {
    it('should prepare, execute and record a successful transaction', async () => {
      mocks.validateTransactionRequirements.mockReturnValue({
        chainId: 1,
        evmChain: 'ethereum',
        fromAddress: '0xfrom',
      });
      mocks.prepareTransactionPayload.mockResolvedValue({
        data: '0xdata',
        from: '0xfrom',
        nonce: 1,
        to: '0xto',
        value: 0n,
      });

      const store = await getStore();
      await store.connect();
      store.connectedAddress = '0xfrom';
      store.connectedChainId = 1;

      const hash = await store.sendTransaction(txParams);

      expect(hash).toBe('0xhash');
      expect(mocks.state.transactionManager.handleTransactionSuccess).toHaveBeenCalledTimes(1);
      expect(get(store.preparing)).toBe(false);
      expect(get(store.waitingForWalletConfirmation)).toBe(false);
    });

    it('should route a failure through handleTransactionError and rethrow', async () => {
      mocks.validateTransactionRequirements.mockImplementation(() => {
        throw new Error('bad requirements');
      });

      const store = await getStore();
      await store.connect();

      await expect(store.sendTransaction(txParams)).rejects.toThrow('bad requirements');
      expect(mocks.handleTransactionError).toHaveBeenCalledTimes(1);
    });

    it('should check the walletconnect connection before sending', async () => {
      mocks.validateTransactionRequirements.mockImplementation(() => {
        throw new Error('stop here');
      });

      const store = await getStore();
      store.walletMode = WALLET_MODES.WALLET_CONNECT;
      await nextTick();

      await expect(store.sendTransaction(txParams)).rejects.toThrow('stop here');
      expect(walletConnect().checkWalletConnection).toHaveBeenCalledTimes(1);
    });
  });
});
