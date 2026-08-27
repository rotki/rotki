import { describe, expect, it } from 'vitest';
import { getWalletNetwork, SUPPORTED_WALLET_NETWORKS } from '@/modules/wallet/chains-viem';

describe('chains-viem', () => {
  it('should carry the chains whose add-network fallback we rely on', () => {
    expect(SUPPORTED_WALLET_NETWORKS.map(network => network.id)).toEqual(
      expect.arrayContaining([1, 143, 999]),
    );
  });

  it('should resolve a network by its chain id', () => {
    expect(getWalletNetwork(143n)?.id).toBe(143);
    expect(getWalletNetwork(999n)?.id).toBe(999);
  });

  it('should return undefined for a chain it has no definition for', () => {
    expect(getWalletNetwork(250n)).toBeUndefined();
  });

  it('should expose the fields wallet_addEthereumChain needs', () => {
    const network = getWalletNetwork(143n);

    expect(network?.name).toBeTruthy();
    expect(network?.nativeCurrency.decimals).toBe(18);
    expect(network?.rpcUrls.default.http[0]).toMatch(/^https:\/\//);
  });
});
