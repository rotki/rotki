import type { EIP1193Provider } from '@/types';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { ref } from 'vue';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useUnifiedProviders } from '../providers/use-unified-providers';
import { useInjectedWallet } from './use-injected-wallet';
import { useWalletProxy } from './use-wallet-proxy';

vi.mock('@vueuse/core', async importOriginal => ({
  ...(await importOriginal<typeof import('@vueuse/core')>()),
  createSharedComposable: <T>(fn: T): T => fn,
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

vi.mock('@/modules/core/common/logging/error-handling', () => ({
  getErrorMessage: vi.fn((error: unknown) => String(error)),
}));

vi.mock('../viem-client', () => ({
  createViemWalletClient: vi.fn(() => ({ __client: true })),
  getAddress: vi.fn((address: string) => address),
}));

const getWalletNetwork = vi.fn();
vi.mock('../chains-viem', () => ({ getWalletNetwork: (chainId: bigint): any => getWalletNetwork(chainId) }));

vi.mock('../providers/use-unified-providers', () => ({ useUnifiedProviders: vi.fn() }));
vi.mock('@/modules/shell/app/use-electron-interop', () => ({ useInterop: vi.fn() }));
vi.mock('./use-wallet-proxy', () => ({ useWalletProxy: vi.fn() }));

const selectedProvider = ref<any>();
let isPackaged: boolean;
let disconnectProxy: Mock;
let startConnectionHealthCheck: Mock;
let stopConnectionHealthCheck: Mock;

interface MockProvider extends EIP1193Provider {
  on: Mock;
  removeListener: Mock;
  request: Mock;
}

function makeProvider(overrides: Partial<MockProvider> = {}): MockProvider {
  return {
    on: vi.fn(),
    removeListener: vi.fn(),
    request: vi.fn(async ({ method }: { method: string }) => {
      if (method === 'eth_requestAccounts')
        return ['0xabc'];
      if (method === 'eth_chainId')
        return '0x1';
      return undefined;
    }),
    ...overrides,
  };
}

function selectProvider(provider: EIP1193Provider, name = 'MetaMask'): void {
  set(selectedProvider, { info: { name, uuid: 'u1' }, provider, source: 'eip6963' });
}

describe('modules/wallet/bridge/use-injected-wallet', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(selectedProvider, undefined);
    isPackaged = false;
    disconnectProxy = vi.fn(async () => {});
    startConnectionHealthCheck = vi.fn();
    stopConnectionHealthCheck = vi.fn();

    vi.mocked(useUnifiedProviders).mockReturnValue(createMock<ReturnType<typeof useUnifiedProviders>>({ selectedProvider }));
    vi.mocked(useInterop).mockReturnValue(createMock<ReturnType<typeof useInterop>>({ isPackaged }));
    vi.mocked(useWalletProxy).mockReturnValue(createMock<ReturnType<typeof useWalletProxy>>({
      disconnectProxy,
      startConnectionHealthCheck,
      stopConnectionHealthCheck,
    }));
  });

  describe('connectToSelectedProvider', () => {
    it('should throw when no provider is selected', async () => {
      const wallet = useInjectedWallet();
      await expect(wallet.connectToSelectedProvider()).rejects.toThrow('No provider selected');
    });

    it('should request accounts, set state and register listeners', async () => {
      const provider = makeProvider();
      selectProvider(provider);
      const wallet = useInjectedWallet();

      await wallet.connectToSelectedProvider();

      expect(get(wallet.connected)).toBe(true);
      expect(get(wallet.connectedAddress)).toBe('0xabc');
      expect(get(wallet.connectedChainId)).toBe(1);
      expect(provider.on).toHaveBeenCalledWith('accountsChanged', expect.any(Function));
      expect(get(wallet.isConnecting)).toBe(false);
    });

    it('should start a health check only when packaged', async () => {
      isPackaged = true;
      vi.mocked(useInterop).mockReturnValue(createMock<ReturnType<typeof useInterop>>({ isPackaged: true }));
      const provider = makeProvider();
      selectProvider(provider);
      const wallet = useInjectedWallet();

      await wallet.connectToSelectedProvider();
      expect(startConnectionHealthCheck).toHaveBeenCalledTimes(1);
    });
  });

  describe('provider events', () => {
    it('should update state from accountsChanged and chainChanged listeners', async () => {
      const provider = makeProvider();
      selectProvider(provider);
      const wallet = useInjectedWallet();
      await wallet.connectToSelectedProvider();

      const calls = provider.on.mock.calls;
      const accountsListener = calls.find(([e]) => e === 'accountsChanged')?.[1];
      const chainListener = calls.find(([e]) => e === 'chainChanged')?.[1];

      accountsListener?.([]);
      expect(get(wallet.connected)).toBe(false);
      expect(get(wallet.connectedAddress)).toBeUndefined();

      chainListener?.('0xa');
      expect(get(wallet.connectedChainId)).toBe(10);
    });
  });

  describe('disconnect', () => {
    it('should revoke permissions, remove listeners and reset state', async () => {
      const provider = makeProvider();
      selectProvider(provider);
      const wallet = useInjectedWallet();
      await wallet.connectToSelectedProvider();

      await wallet.disconnect();

      expect(stopConnectionHealthCheck).toHaveBeenCalled();
      expect(provider.request).toHaveBeenCalledWith({ method: 'wallet_revokePermissions', params: [{ eth_accounts: {} }] });
      expect(provider.removeListener).toHaveBeenCalled();
      expect(get(wallet.connected)).toBe(false);
      expect(get(wallet.connectedAddress)).toBeUndefined();
    });

    it('should disconnect the proxy when packaged', async () => {
      vi.mocked(useInterop).mockReturnValue(createMock<ReturnType<typeof useInterop>>({ isPackaged: true }));
      const provider = makeProvider();
      selectProvider(provider);
      const wallet = useInjectedWallet();
      await wallet.connectToSelectedProvider();

      await wallet.disconnect();
      expect(disconnectProxy).toHaveBeenCalledTimes(1);
    });
  });

  describe('getWalletClient', () => {
    it('should throw before a provider is connected', () => {
      const wallet = useInjectedWallet();
      expect(() => wallet.getWalletClient()).toThrow('Injected provider not initialized');
    });

    it('should build a viem client once connected', async () => {
      const provider = makeProvider();
      selectProvider(provider);
      const wallet = useInjectedWallet();
      await wallet.connectToSelectedProvider();

      expect(wallet.getWalletClient()).toEqual({ __client: true });
    });
  });

  describe('switchNetwork', () => {
    it('should request a chain switch and refresh the chain id', async () => {
      const provider = makeProvider();
      selectProvider(provider);
      const wallet = useInjectedWallet();
      await wallet.connectToSelectedProvider();
      vi.mocked(provider.request).mockClear();

      await wallet.switchNetwork(10n);
      expect(provider.request).toHaveBeenCalledWith({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: '0xa' }],
      });
    });

    it('should add the chain when the wallet does not know it (4902)', async () => {
      const request = vi.fn()
        .mockImplementationOnce(async () => ['0xabc']) // eth_requestAccounts
        .mockImplementationOnce(async () => '0x1') // eth_chainId
        .mockImplementationOnce(async () => { throw Object.assign(new Error('unknown chain'), { code: 4902 }); })
        .mockImplementation(async () => undefined);
      const provider = makeProvider({ request });
      selectProvider(provider);
      getWalletNetwork.mockReturnValue({
        blockExplorers: { default: { url: 'https://explorer' } },
        name: 'Optimism',
        nativeCurrency: { decimals: 18, name: 'Ether', symbol: 'ETH' },
        rpcUrls: { default: { http: ['https://rpc.op'] } },
      });
      const wallet = useInjectedWallet();
      await wallet.connectToSelectedProvider();

      await wallet.switchNetwork(10n);

      expect(request).toHaveBeenCalledWith(expect.objectContaining({ method: 'wallet_addEthereumChain' }));
    });

    it('should send an empty explorer list when the chain has no explorer', async () => {
      const request = vi.fn()
        .mockImplementationOnce(async () => ['0xabc']) // eth_requestAccounts
        .mockImplementationOnce(async () => '0x1') // eth_chainId
        .mockImplementationOnce(async () => { throw Object.assign(new Error('unknown chain'), { code: 4902 }); })
        .mockImplementation(async () => undefined);
      const provider = makeProvider({ request });
      selectProvider(provider);
      getWalletNetwork.mockReturnValue({
        name: 'Monad',
        nativeCurrency: { decimals: 18, name: 'Monad', symbol: 'MON' },
        rpcUrls: { default: { http: ['https://rpc.monad'] } },
      });
      const wallet = useInjectedWallet();
      await wallet.connectToSelectedProvider();

      await wallet.switchNetwork(143n);

      expect(request).toHaveBeenCalledWith(expect.objectContaining({
        method: 'wallet_addEthereumChain',
        params: [expect.objectContaining({ blockExplorerUrls: [] })],
      }));
    });

    it('should surface the 4902 when it has no definition for the chain, the dynamic chain list naming chains the viem table lacks', async () => {
      const request = vi.fn()
        .mockImplementationOnce(async () => ['0xabc']) // eth_requestAccounts
        .mockImplementationOnce(async () => '0x1') // eth_chainId
        .mockImplementationOnce(async () => { throw Object.assign(new Error('unknown chain'), { code: 4902 }); })
        .mockImplementation(async () => undefined);
      const provider = makeProvider({ request });
      selectProvider(provider);
      getWalletNetwork.mockReturnValue(undefined);
      const wallet = useInjectedWallet();
      await wallet.connectToSelectedProvider();

      // Swallowing it leaves the user with a click that silently does nothing.
      await expect(wallet.switchNetwork(143n)).rejects.toThrow('unknown chain');
      expect(request).not.toHaveBeenCalledWith(expect.objectContaining({ method: 'wallet_addEthereumChain' }));
    });
  });
});
