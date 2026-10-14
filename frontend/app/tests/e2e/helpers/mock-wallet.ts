import type { Page } from '@playwright/test';

interface MockWalletOptions {
  /** The account the wallet hands out on `eth_requestAccounts`. */
  address: string;
  /** Hex chain id the wallet reports, `0x1` (Ethereum) unless given. */
  chainId?: string;
}

/** What the wallet returns for every transaction it is asked to send. */
export const MOCK_TX_HASH = `0x${'cd'.repeat(32)}`;

declare global {
  interface Window {
    /** Set to make the mock wallet turn down the next transactions, as a user rejecting them would. */
    mockWalletRejects?: boolean;
  }
}

/**
 * Installs a browser wallet the send page can connect to, standing in for an extension.
 *
 * @remarks
 * It announces itself over EIP-6963, the way a real extension does, and answers what connecting,
 * switching networks, estimating gas and sending ask of it: 2 ETH of balance, a 1 gwei gas price,
 * and a transaction that is mined at once, its receipt reporting success. The page asks for
 * providers when the user connects, not on load, so installing it after navigation is enough. The
 * backend still prepares the transfer, so a test that sends stubs that endpoint as well.
 */
export async function installMockWallet(page: Page, options: MockWalletOptions): Promise<void> {
  await page.evaluate(({ address, chainId: initialChainId, hash }) => {
    let chainId = initialChainId;
    const listeners: Record<string, ((value: unknown) => void)[]> = {};
    const emit = (event: string, value: unknown): void => {
      for (const listener of listeners[event] ?? [])
        listener(value);
    };

    const zeros = (length: number): string => `0x${'0'.repeat(length)}`;
    const block = {
      baseFeePerGas: '0x3b9aca00',
      difficulty: '0x0',
      extraData: '0x',
      gasLimit: '0x1c9c380',
      gasUsed: '0x0',
      hash: `0x${'1'.repeat(64)}`,
      logsBloom: zeros(512),
      miner: zeros(40),
      mixHash: zeros(64),
      nonce: '0x0000000000000000',
      number: '0x1312d00',
      parentHash: zeros(64),
      receiptsRoot: zeros(64),
      sha3Uncles: zeros(64),
      size: '0x0',
      stateRoot: zeros(64),
      timestamp: '0x6700000',
      totalDifficulty: '0x0',
      transactions: [],
      transactionsRoot: zeros(64),
      uncles: [],
    };
    const receipt = {
      blockHash: block.hash,
      blockNumber: block.number,
      contractAddress: null,
      cumulativeGasUsed: '0x5208',
      effectiveGasPrice: '0x3b9aca00',
      from: address,
      gasUsed: '0x5208',
      logs: [],
      logsBloom: zeros(512),
      status: '0x1',
      to: zeros(40),
      transactionHash: hash,
      transactionIndex: '0x0',
      type: '0x0',
    };

    const handlers: Record<string, (params: unknown[]) => unknown> = {
      eth_accounts: () => [address],
      eth_blockNumber: () => '0x1312d05',
      eth_chainId: () => chainId,
      eth_estimateGas: () => '0x5208',
      eth_gasPrice: () => '0x3b9aca00',
      eth_getBalance: () => '0x1bc16d674ec80000',
      eth_getBlockByNumber: () => block,
      eth_getTransactionByHash: () => ({ ...receipt, chainId, gas: '0x5208', gasPrice: '0x3b9aca00', hash, input: '0x', nonce: '0x1', r: '0x1', s: '0x1', v: '0x1b', value: '0x0' }),
      eth_getTransactionReceipt: () => receipt,
      eth_requestAccounts: () => [address],
      eth_sendTransaction: () => {
        if (window.mockWalletRejects)
          throw Object.assign(new Error('User rejected the request.'), { code: 4001 });
        return hash;
      },
      wallet_revokePermissions: () => null,
      wallet_switchEthereumChain: (params) => {
        const [target] = params;
        if (typeof target === 'object' && target !== null && 'chainId' in target && typeof target.chainId === 'string')
          chainId = target.chainId;
        setTimeout(emit, 50, 'chainChanged', chainId);
        return null;
      },
    };

    interface MockProvider {
      on: (event: string, listener: (value: unknown) => void) => MockProvider;
      removeListener: (event: string, listener: (value: unknown) => void) => MockProvider;
      request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
    }

    const provider: MockProvider = {
      on(event: string, listener: (value: unknown) => void): MockProvider {
        (listeners[event] ??= []).push(listener);
        return provider;
      },
      removeListener(event: string, listener: (value: unknown) => void): MockProvider {
        listeners[event] = (listeners[event] ?? []).filter(item => item !== listener);
        return provider;
      },
      async request({ method, params }: { method: string; params?: unknown[] }): Promise<unknown> {
        const handler = handlers[method];
        if (!handler)
          throw Object.assign(new Error(`MockWallet: ${method} not supported`), { code: 4200 });
        return handler(params ?? []);
      },
    };

    const info = {
      icon: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMiAzMiI+PGNpcmNsZSBjeD0iMTYiIGN5PSIxNiIgcj0iMTYiIGZpbGw9IiM2MzY2ZjEiLz48L3N2Zz4=',
      name: 'Mock Wallet',
      rdns: 'dev.rotki.mockwallet',
      uuid: '6f1d3c3e-0000-4000-8000-000000000001',
    };
    const announce = (): void => {
      window.dispatchEvent(new CustomEvent('eip6963:announceProvider', { detail: Object.freeze({ info, provider }) }));
    };
    window.addEventListener('eip6963:requestProvider', announce);
    announce();
  }, { address: options.address, chainId: options.chainId ?? '0x1', hash: MOCK_TX_HASH });
}

/** Makes the mock wallet reject (or accept again) the transactions it is asked to send. */
export async function setMockWalletRejects(page: Page, rejects: boolean): Promise<void> {
  await page.evaluate((value) => {
    window.mockWalletRejects = value;
  }, rejects);
}
