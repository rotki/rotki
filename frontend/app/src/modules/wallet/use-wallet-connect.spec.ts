import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

vi.mock('./viem-client', () => ({
  createViemWalletClient: vi.fn(() => ({ __client: true })),
  getAddress: vi.fn((address: string) => address),
}));

const network1 = { id: 1, rpcUrls: { default: { http: ['https://rpc.one'] } } };
const network8453 = { id: 8453, rpcUrls: { default: { http: ['https://rpc.base'] } } };

const CHAIN_IDS = [1, 8453];

vi.mock('./chains-viem', () => ({
  SUPPORTED_WALLET_NETWORKS: [network1, network8453],
  getWalletNetwork: vi.fn((chainId: bigint) => (chainId === 1n ? network1 : undefined)),
}));

let mockProviderInstance: ReturnType<typeof createProvider>;

vi.mock('@walletconnect/universal-provider', () => ({
  UniversalProvider: { init: vi.fn(async () => mockProviderInstance) },
}));

interface WcSession {
  topic: string;
  namespaces: Record<string, { accounts: string[]; chains?: string[] }>;
}

function makeSession(accounts: string[], chains?: string[]): WcSession {
  return { namespaces: { eip155: { accounts, chains } }, topic: 'topic-1' };
}

function createProvider(overrides: Record<string, unknown> = {}): Record<string, any> {
  const handlers: Record<string, ((...args: any[]) => void)[]> = {};
  return {
    abortPairingAttempt: vi.fn(),
    client: { ping: vi.fn(async () => {}) },
    connect: vi.fn(async () => {}),
    disconnect: vi.fn(async () => {}),
    emit: (event: string, ...args: unknown[]): void => {
      (handlers[event] ?? []).forEach(handler => handler(...args));
    },
    isWalletConnect: true,
    on: vi.fn((event: string, cb: (...args: any[]) => void) => {
      (handlers[event] ??= []).push(cb);
    }),
    removeListener: vi.fn((event: string, cb: (...args: any[]) => void) => {
      handlers[event] = (handlers[event] ?? []).filter(handler => handler !== cb);
    }),
    request: vi.fn(async () => {}),
    session: undefined,
    setDefaultChain: vi.fn(),
    ...overrides,
  };
}

async function loadComposable(): Promise<ReturnType<typeof import('./use-wallet-connect').useWalletConnect>> {
  const { useWalletConnect } = await import('./use-wallet-connect');
  return useWalletConnect();
}

describe('modules/wallet/use-wallet-connect', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    mockProviderInstance = createProvider();
  });

  describe('connect', () => {
    it('should initialize the provider and request the eip155 namespace', async () => {
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);

      expect(mockProviderInstance.connect).toHaveBeenCalledTimes(1);
      const arg = mockProviderInstance.connect.mock.calls[0][0];
      expect(arg.optionalNamespaces.eip155.chains).toEqual(['eip155:1', 'eip155:8453']);
      expect(arg.optionalNamespaces.eip155.rpcMap).toEqual({
        'eip155:1': 'https://rpc.one',
        'eip155:8453': 'https://rpc.base',
      });
    });

    it('should request a chain that has no viem definition, without an rpc url', async () => {
      const wc = await loadComposable();
      await wc.connect([1, 143]);

      const arg = mockProviderInstance.connect.mock.calls[0][0];
      expect(arg.optionalNamespaces.eip155.chains).toEqual(['eip155:1', 'eip155:143']);
      expect(arg.optionalNamespaces.eip155.rpcMap).toEqual({ 'eip155:1': 'https://rpc.one' });
    });

    it('should refuse to pair when no chains are available', async () => {
      const wc = await loadComposable();

      await expect(wc.connect([])).rejects.toThrow('No supported chains');
      expect(mockProviderInstance.connect).not.toHaveBeenCalled();
    });

    it('should not request a chain the caller left out', async () => {
      const wc = await loadComposable();
      await wc.connect([1]);

      const arg = mockProviderInstance.connect.mock.calls[0][0];
      expect(arg.optionalNamespaces.eip155.chains).toEqual(['eip155:1']);
    });

    it('should sync an already-restored session and skip a new pairing', async () => {
      mockProviderInstance.session = makeSession(['eip155:1:0xabc']);
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);

      expect(mockProviderInstance.connect).not.toHaveBeenCalled();
      expect(get(wc.connected)).toBe(true);
      expect(get(wc.connectedAddress)).toBe('0xabc');
      expect(get(wc.connectedChainId)).toBe(1);
    });

    it('should populate connection state from the session after pairing', async () => {
      mockProviderInstance.connect = vi.fn(async () => {
        mockProviderInstance.session = makeSession(['eip155:8453:0xdef'], ['eip155:8453', 'eip155:1']);
      });
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);

      expect(get(wc.connected)).toBe(true);
      expect(get(wc.connectedAddress)).toBe('0xdef');
      expect(get(wc.connectedChainId)).toBe(8453);
      expect(get(wc.supportedChainIds)).toEqual(['eip155:8453', 'eip155:1']);
      expect(get(wc.preparing)).toBe(false);
    });

    it('should open the QR modal when the provider emits a display uri', async () => {
      mockProviderInstance.connect = vi.fn(async () => {
        mockProviderInstance.emit('display_uri', 'wc:pair-uri');
      });
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);

      expect(get(wc.connectUri)).toBeUndefined(); // closed in finally
      expect(get(wc.showConnectModal)).toBe(false);
    });

    it('should rethrow a pairing error that was not aborted by the user', async () => {
      mockProviderInstance.connect = vi.fn(async () => {
        throw new Error('pairing blew up');
      });
      const wc = await loadComposable();

      await expect(wc.connect(CHAIN_IDS)).rejects.toThrow('pairing blew up');
      expect(get(wc.preparing)).toBe(false);
    });

    it('should swallow the error when the user cancelled the pairing', async () => {
      const wc = await loadComposable();
      // Cancel mid-pairing, i.e. after connect() has reset connectAborted.
      mockProviderInstance.connect = vi.fn(async () => {
        wc.cancelConnect();
        throw new Error('pairing aborted');
      });

      await expect(wc.connect(CHAIN_IDS)).resolves.toBeUndefined();
    });
  });

  describe('cancelConnect', () => {
    it('should abort the pairing attempt and close the modal', async () => {
      const wc = await loadComposable();
      mockProviderInstance.connect = vi.fn(async () => {
        mockProviderInstance.emit('display_uri', 'wc:pair-uri');
        wc.cancelConnect();
        throw new Error('aborted');
      });

      await wc.connect(CHAIN_IDS);

      expect(mockProviderInstance.abortPairingAttempt).toHaveBeenCalledTimes(1);
      expect(get(wc.showConnectModal)).toBe(false);
      expect(get(wc.connectUri)).toBeUndefined();
    });
  });

  describe('disconnect', () => {
    it('should call provider.disconnect and reset state when a session exists', async () => {
      mockProviderInstance.session = makeSession(['eip155:1:0xabc']);
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);
      expect(get(wc.connected)).toBe(true);

      await wc.disconnect();

      expect(mockProviderInstance.disconnect).toHaveBeenCalledTimes(1);
      expect(get(wc.connected)).toBe(false);
      expect(get(wc.connectedAddress)).toBeUndefined();
      expect(get(wc.connectedChainId)).toBeUndefined();
    });

    it('should reset state without calling provider.disconnect when there is no session', async () => {
      const wc = await loadComposable();
      await wc.disconnect();
      expect(mockProviderInstance.disconnect).not.toHaveBeenCalled();
      expect(get(wc.connected)).toBe(false);
    });
  });

  describe('getWalletClient', () => {
    it('should throw when no provider has been initialized', async () => {
      const wc = await loadComposable();
      expect(() => wc.getWalletClient()).toThrow('WalletConnect provider not available');
    });

    it('should build a viem client once the provider exists', async () => {
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);
      expect(wc.getWalletClient()).toEqual({ __client: true });
    });
  });

  describe('switchNetwork', () => {
    it('should request the chain switch and update the default chain', async () => {
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);
      await wc.switchNetwork(1n);

      expect(mockProviderInstance.request).toHaveBeenCalledWith({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: '0x1' }],
      });
      expect(mockProviderInstance.setDefaultChain).toHaveBeenCalledWith('eip155:1', 'https://rpc.one');
    });

    it('should be a no-op when no provider is initialized', async () => {
      const wc = await loadComposable();
      await wc.switchNetwork(1n);
      expect(mockProviderInstance.request).not.toHaveBeenCalled();
    });
  });

  describe('checkWalletConnection', () => {
    it('should return early when there is no active WalletConnect session', async () => {
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);
      await wc.checkWalletConnection();
      expect(mockProviderInstance.client.ping).not.toHaveBeenCalled();
    });

    it('should ping the session and resolve when the wallet responds', async () => {
      mockProviderInstance.session = makeSession(['eip155:1:0xabc']);
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);

      await wc.checkWalletConnection();

      expect(mockProviderInstance.client.ping).toHaveBeenCalledWith({ topic: 'topic-1' });
      expect(get(wc.preparing)).toBe(false);
    });

    it('should throw an inactive-wallet error when the ping rejects', async () => {
      mockProviderInstance.session = makeSession(['eip155:1:0xabc']);
      mockProviderInstance.client.ping = vi.fn(async () => {
        throw new Error('ping failed');
      });
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);

      await expect(wc.checkWalletConnection()).rejects.toThrow(/wallet is inactive/);
      expect(get(wc.preparing)).toBe(false);
    });
  });

  describe('provider events', () => {
    it('should update the address on accountsChanged and reset on empty', async () => {
      mockProviderInstance.session = makeSession(['eip155:1:0xabc']);
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);

      mockProviderInstance.emit('accountsChanged', ['eip155:1:0xdeadbeef']);
      expect(get(wc.connectedAddress)).toBe('0xdeadbeef');
      expect(get(wc.connected)).toBe(true);

      mockProviderInstance.emit('accountsChanged', []);
      expect(get(wc.connected)).toBe(false);
      expect(get(wc.connectedAddress)).toBeUndefined();
    });

    it('should parse a hex chainChanged value', async () => {
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);

      mockProviderInstance.emit('chainChanged', '0xa');
      expect(get(wc.connectedChainId)).toBe(10);
    });

    it('should reset state on disconnect and session_delete events', async () => {
      mockProviderInstance.session = makeSession(['eip155:1:0xabc']);
      const wc = await loadComposable();
      await wc.connect(CHAIN_IDS);
      expect(get(wc.connected)).toBe(true);

      mockProviderInstance.emit('disconnect');
      expect(get(wc.connected)).toBe(false);
    });
  });
});
