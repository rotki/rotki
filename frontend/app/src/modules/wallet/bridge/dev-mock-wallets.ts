interface MockWalletOptions {
  count: number;
  /** Make the wallets turn down connection and transaction requests, as a user rejecting them would. */
  rejects?: boolean;
}

interface MockRequest {
  method: string;
  params?: unknown[];
}

type MockListener = (value: unknown) => void;

/** Hardhat's public development accounts, so nothing here can ever be mistaken for real funds. */
const MOCK_ADDRESSES = [
  '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266',
  '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
  '0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC',
] as const;

const MOCK_TX_HASH = `0x${'cd'.repeat(32)}`;

const USER_REJECTED_CODE = 4001;

const UNSUPPORTED_METHOD_CODE = 4200;

function createRpcError(message: string, code: number): Error {
  return Object.assign(new Error(message), { code });
}

function iconFor(index: number): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><circle cx="16" cy="16" r="16" fill="hsl(${index * 90 + 220} 70% 55%)"/></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function createMockProvider(address: string, rejects: boolean): Record<string, unknown> {
  const listeners = new Map<string, Set<MockListener>>();
  let connected = false;
  let chainId = '0x1';

  const emit = (event: string, value: unknown): void => {
    for (const listener of listeners.get(event) ?? [])
      listener(value);
  };

  const accepted = (): void => {
    if (rejects)
      throw createRpcError('User rejected the request.', USER_REJECTED_CODE);
  };

  const handlers = new Map<string, (params: unknown[]) => unknown>([
    ['eth_accounts', (): string[] => (connected ? [address] : [])],
    ['eth_blockNumber', (): string => '0x1312d05'],
    ['eth_chainId', (): string => chainId],
    ['eth_estimateGas', (): string => '0x5208'],
    ['eth_gasPrice', (): string => '0x3b9aca00'],
    ['eth_getBalance', (): string => '0x1bc16d674ec80000'],
    ['eth_requestAccounts', (): string[] => {
      accepted();
      connected = true;
      emit('accountsChanged', [address]);
      return [address];
    }],
    ['eth_sendTransaction', (): string => {
      accepted();
      return MOCK_TX_HASH;
    }],
    ['wallet_addEthereumChain', (): null => null],
    ['wallet_revokePermissions', (): null => {
      connected = false;
      emit('accountsChanged', []);
      return null;
    }],
    ['wallet_switchEthereumChain', ([target]): null => {
      const next: unknown = typeof target === 'object' && target !== null ? Reflect.get(target, 'chainId') : undefined;
      if (typeof next === 'string') {
        chainId = next;
        emit('chainChanged', chainId);
      }
      return null;
    }],
  ]);

  return {
    on(event: string, listener: MockListener): void {
      const registered = listeners.get(event) ?? new Set<MockListener>();
      registered.add(listener);
      listeners.set(event, registered);
    },
    removeListener(event: string, listener: MockListener): void {
      listeners.get(event)?.delete(listener);
    },
    async request({ method, params }: MockRequest): Promise<unknown> {
      const handler = handlers.get(method);
      if (!handler)
        throw createRpcError(`Mock wallet: ${method} not supported`, UNSUPPORTED_METHOD_CODE);
      return handler(params ?? []);
    },
  };
}

/**
 * Announces fake wallets over EIP-6963, so the bridge can be exercised without an extension.
 *
 * @remarks
 * Development only: the bridge page reaches this through a dynamic import guarded by
 * `import.meta.env.DEV`, so it never ships. They connect, switch chains and "send" without touching
 * any network, but do not answer the block and receipt reads a full send flow needs. For that, see
 * `tests/e2e/helpers/mock-wallet.ts`.
 *
 * @returns a function that stops announcing them
 */
export function installMockWallets({ count, rejects = false }: MockWalletOptions): () => void {
  const wallets = Array.from({ length: Math.min(count, MOCK_ADDRESSES.length) }, (_, index) => ({
    info: {
      icon: iconFor(index),
      name: `Mock Wallet ${index + 1}`,
      rdns: `dev.rotki.mockwallet${index + 1}`,
      uuid: `6f1d3c3e-0000-4000-8000-00000000000${index + 1}`,
    },
    provider: createMockProvider(MOCK_ADDRESSES[index], rejects),
  }));

  const announce = (): void => {
    for (const detail of wallets)
      window.dispatchEvent(new CustomEvent('eip6963:announceProvider', { detail: Object.freeze(detail) }));
  };

  window.addEventListener('eip6963:requestProvider', announce);
  announce();
  return (): void => window.removeEventListener('eip6963:requestProvider', announce);
}
