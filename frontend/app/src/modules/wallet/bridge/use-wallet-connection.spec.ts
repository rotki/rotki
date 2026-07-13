import type { EIP1193Provider, EIP1193ProviderEvents } from '@/types';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { useWalletConnection } from '@/modules/wallet/bridge/use-wallet-connection';

// A lowercase address and its checksummed form (real viem getAddress runs unmocked).
const LOWER_ADDRESS = '0x5a0b54d5dc17e0aadc383d2db43b0a0d3e029c4c';
const CHECKSUM_ADDRESS = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

type Listeners = Map<string, (...args: any[]) => void>;

type RequestMock = Mock<(args: { method: string; params?: unknown }) => Promise<any>>;

interface ProviderHarness {
  provider: EIP1193Provider;
  listeners: Listeners;
  request: RequestMock;
}

function createProvider(overrides: Partial<EIP1193Provider> = {}): ProviderHarness {
  const listeners: Listeners = new Map();
  const request: RequestMock = vi.fn();
  const provider: EIP1193Provider = {
    on: vi.fn((event: keyof EIP1193ProviderEvents, cb: (...args: any[]) => void) => {
      listeners.set(event, cb);
    }),
    removeListener: vi.fn((event: keyof EIP1193ProviderEvents) => {
      listeners.delete(event);
    }),
    request,
    ...overrides,
  };
  return { listeners, provider, request };
}

describe('useWalletConnection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should default all connection refs to undefined/false', () => {
    const { connectedAddress, connectedChainId, connectionError, isConnecting } = useWalletConnection();
    expect(get(connectedAddress)).toBeUndefined();
    expect(get(connectedChainId)).toBeUndefined();
    expect(get(connectionError)).toBeUndefined();
    expect(get(isConnecting)).toBe(false);
  });

  it('should set a connection error message and return it for Error inputs', () => {
    const { connectionError, handleConnectionError } = useWalletConnection();
    const message = handleConnectionError(new Error('boom'), 'connect wallet');
    expect(message).toBe('boom');
    expect(get(connectionError)).toBe('boom');
  });

  it('should fall back to a context message for non-object errors', () => {
    const { connectionError, handleConnectionError } = useWalletConnection();
    const message = handleConnectionError('nope', 'connect wallet');
    expect(message).toBe('Failed to connect wallet');
    expect(get(connectionError)).toBe('Failed to connect wallet');
  });

  it('should reset the connection error', () => {
    const { connectionError, handleConnectionError, resetError } = useWalletConnection();
    handleConnectionError(new Error('boom'), 'x');
    expect(get(connectionError)).toBe('boom');
    resetError();
    expect(get(connectionError)).toBeUndefined();
  });

  it('should connect and store the checksummed address and chain id', async () => {
    const { provider, request } = createProvider();
    request.mockImplementation(async ({ method }: { method: string }) => {
      if (method === 'eth_requestAccounts')
        return [LOWER_ADDRESS];
      if (method === 'eth_chainId')
        return '0xa';
      return undefined;
    });

    const { connectToProvider, connectedAddress, connectedChainId, isConnecting } = useWalletConnection();
    await connectToProvider(provider);

    expect(get(connectedAddress)).toBe(CHECKSUM_ADDRESS);
    expect(get(connectedChainId)).toBe(10);
    expect(get(isConnecting)).toBe(false);
  });

  it('should throw and clear state when no accounts are returned', async () => {
    const { provider, request } = createProvider();
    request.mockResolvedValue([]);

    const { connectToProvider, connectedAddress, connectionError, isConnecting } = useWalletConnection();
    await expect(connectToProvider(provider)).rejects.toThrow('No accounts returned from wallet.');

    expect(get(connectedAddress)).toBeUndefined();
    // handleConnectionError set the error, then clearConnectionState reset it.
    expect(get(connectionError)).toBeUndefined();
    expect(get(isConnecting)).toBe(false);
  });

  it('should rethrow and reset isConnecting when the request fails', async () => {
    const { provider, request } = createProvider();
    request.mockRejectedValue(new Error('rpc down'));

    const { connectToProvider, connectedAddress, isConnecting } = useWalletConnection();
    await expect(connectToProvider(provider)).rejects.toThrow('rpc down');
    expect(get(connectedAddress)).toBeUndefined();
    expect(get(isConnecting)).toBe(false);
  });

  it('should register listeners and query the current provider state on setup', async () => {
    const { provider, listeners, request } = createProvider();
    request.mockImplementation(async ({ method }: { method: string }) => {
      if (method === 'eth_accounts')
        return [LOWER_ADDRESS];
      if (method === 'eth_chainId')
        return '0x1';
      return undefined;
    });

    const { setupProvider, connectedAddress, connectedChainId } = useWalletConnection();
    await setupProvider(provider);

    expect(listeners.has('accountsChanged')).toBe(true);
    expect(listeners.has('chainChanged')).toBe(true);
    expect(get(connectedAddress)).toBe(CHECKSUM_ADDRESS);
    expect(get(connectedChainId)).toBe(1);
  });

  it('should swallow errors thrown while querying provider state on setup', async () => {
    const { provider, request } = createProvider();
    request.mockRejectedValue(new Error('not connected'));

    const { setupProvider, connectedAddress } = useWalletConnection();
    await expect(setupProvider(provider)).resolves.toBeUndefined();
    expect(get(connectedAddress)).toBeUndefined();
  });

  it('should skip listener registration when the provider has no on()', async () => {
    const { provider } = createProvider({ on: undefined });
    const { setupProvider, connectedAddress } = useWalletConnection();
    await expect(setupProvider(provider)).resolves.toBeUndefined();
    expect(get(connectedAddress)).toBeUndefined();
  });

  it('should update the address via the accountsChanged listener', async () => {
    const { provider, listeners, request } = createProvider();
    request.mockResolvedValue(undefined);

    const { setupProvider, connectedAddress } = useWalletConnection();
    await setupProvider(provider);

    listeners.get('accountsChanged')?.([LOWER_ADDRESS]);
    expect(get(connectedAddress)).toBe(CHECKSUM_ADDRESS);

    listeners.get('accountsChanged')?.([]);
    expect(get(connectedAddress)).toBeUndefined();
  });

  it('should update the chain id via the chainChanged listener', async () => {
    const { provider, listeners, request } = createProvider();
    request.mockResolvedValue(undefined);

    const { setupProvider, connectedChainId } = useWalletConnection();
    await setupProvider(provider);

    listeners.get('chainChanged')?.('0x89');
    expect(get(connectedChainId)).toBe(137);
  });

  it('should remove listeners on cleanupProviderListeners', async () => {
    const { provider, request } = createProvider();
    request.mockResolvedValue(undefined);

    const { setupProvider, cleanupProviderListeners } = useWalletConnection();
    await setupProvider(provider);
    cleanupProviderListeners();

    expect(provider.removeListener).toHaveBeenCalledWith('accountsChanged', expect.any(Function));
    expect(provider.removeListener).toHaveBeenCalledWith('chainChanged', expect.any(Function));
  });

  it('should clean up the previous provider when setting up a new one', async () => {
    const first = createProvider();
    const second = createProvider();
    first.request.mockResolvedValue(undefined);
    second.request.mockResolvedValue(undefined);

    const { setupProvider } = useWalletConnection();
    await setupProvider(first.provider);
    await setupProvider(second.provider);

    expect(first.provider.removeListener).toHaveBeenCalled();
  });

  it('should disconnect, revoke permissions and clear state', async () => {
    const disconnect = vi.fn().mockResolvedValue(undefined);
    const { provider, request } = createProvider({ disconnect });
    request.mockResolvedValue(undefined);

    const { disconnectFromProvider, connectedAddress } = useWalletConnection();
    await disconnectFromProvider(provider);

    expect(disconnect).toHaveBeenCalledOnce();
    expect(request).toHaveBeenCalledWith({
      method: 'wallet_revokePermissions',
      params: [{ eth_accounts: {} }],
    });
    expect(get(connectedAddress)).toBeUndefined();
  });

  it('should still clear state when the provider lacks disconnect()', async () => {
    const { provider, request } = createProvider({ disconnect: undefined });
    request.mockResolvedValue(undefined);

    const { disconnectFromProvider } = useWalletConnection();
    await expect(disconnectFromProvider(provider)).resolves.toBeUndefined();
    expect(request).toHaveBeenCalledWith(expect.objectContaining({ method: 'wallet_revokePermissions' }));
  });

  it('should swallow a failing disconnect() and continue', async () => {
    const disconnect = vi.fn().mockRejectedValue(new Error('unsupported'));
    const { provider, request } = createProvider({ disconnect });
    request.mockResolvedValue(undefined);

    const { disconnectFromProvider } = useWalletConnection();
    await expect(disconnectFromProvider(provider)).resolves.toBeUndefined();
    expect(request).toHaveBeenCalledWith(expect.objectContaining({ method: 'wallet_revokePermissions' }));
  });

  it('should clear provider and connection state via clearProvider', async () => {
    const { provider, request } = createProvider();
    request.mockImplementation(async ({ method }: { method: string }) =>
      method === 'eth_accounts' ? [LOWER_ADDRESS] : '0x1');

    const { setupProvider, clearProvider, connectedAddress, connectedChainId } = useWalletConnection();
    await setupProvider(provider);
    expect(get(connectedAddress)).toBe(CHECKSUM_ADDRESS);

    clearProvider();
    expect(get(connectedAddress)).toBeUndefined();
    expect(get(connectedChainId)).toBeUndefined();
    expect(provider.removeListener).toHaveBeenCalled();
  });
});
