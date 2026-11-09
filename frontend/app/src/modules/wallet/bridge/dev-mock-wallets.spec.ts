import type { EIP1193Provider, EIP6963AnnounceProviderEvent, EIP6963ProviderDetail } from '@/types';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { getAllWalletProviders } from '../providers/provider-detection';
import { installMockWallets } from './dev-mock-wallets';

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

vi.mock('./use-proxy-provider', () => ({
  useProxyProvider: vi.fn(),
}));

describe('modules/wallet/bridge/dev-mock-wallets', () => {
  let uninstall: (() => void) | undefined;

  afterEach(() => {
    uninstall?.();
    uninstall = undefined;
  });

  async function detect(count: number, rejects = false): Promise<EIP6963ProviderDetail[]> {
    uninstall = installMockWallets({ count, rejects });
    return getAllWalletProviders({ includeLegacy: false, timeout: 0 });
  }

  async function firstProvider(rejects = false): Promise<EIP1193Provider> {
    const [wallet] = await detect(1, rejects);
    return wallet.provider;
  }

  it('should be found by the real detection, once per wallet', async () => {
    const wallets = await detect(2);

    expect(wallets.map(wallet => wallet.info.name)).toEqual(['Mock Wallet 1', 'Mock Wallet 2']);
  });

  it('should stop answering detection once uninstalled', async () => {
    installMockWallets({ count: 1 })();
    const seen = vi.fn<(event: EIP6963AnnounceProviderEvent) => void>();

    window.addEventListener('eip6963:announceProvider', seen);
    window.dispatchEvent(new Event('eip6963:requestProvider'));
    window.removeEventListener('eip6963:announceProvider', seen);

    expect(seen).not.toHaveBeenCalled();
  });

  it('should share no accounts until connected, and none after permissions are revoked', async () => {
    const provider = await firstProvider();

    await expect(provider.request({ method: 'eth_accounts', params: [] })).resolves.toEqual([]);
    const [address] = await provider.request<string[]>({ method: 'eth_requestAccounts', params: [] });
    await expect(provider.request({ method: 'eth_accounts', params: [] })).resolves.toEqual([address]);

    await provider.request({ method: 'wallet_revokePermissions', params: [] });
    await expect(provider.request({ method: 'eth_accounts', params: [] })).resolves.toEqual([]);
  });

  it('should report the new chain after a switch', async () => {
    const provider = await firstProvider();
    const chainChanged = vi.fn<(chainId: string) => void>();
    provider.on?.('chainChanged', chainChanged);

    await provider.request({ method: 'wallet_switchEthereumChain', params: [{ chainId: '0x89' }] });

    expect(chainChanged).toHaveBeenCalledWith('0x89');
    await expect(provider.request({ method: 'eth_chainId', params: [] })).resolves.toBe('0x89');
  });

  it('should reject connecting with the user-rejected code when asked to', async () => {
    const provider = await firstProvider(true);

    await expect(provider.request({ method: 'eth_requestAccounts', params: [] })).rejects.toMatchObject({ code: 4001 });
  });

  it('should fail an unknown method with the unsupported code', async () => {
    const provider = await firstProvider();

    await expect(provider.request({ method: 'eth_nope', params: [] })).rejects.toMatchObject({ code: 4200 });
  });
});
