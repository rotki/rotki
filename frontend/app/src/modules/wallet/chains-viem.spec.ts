import { describe, expect, it } from 'vitest';
import { getWalletNetwork, SUPPORTED_WALLET_NETWORKS } from '@/modules/wallet/chains-viem';

// The seam: this table only enriches a chain with an rpc url and the payload for
// `wallet_addEthereumChain`. It does not decide which chains the wallet offers,
// so a missing entry must return undefined rather than a wrong chain.

describe('chains-viem', () => {
  it('should carry the chains whose add-network fallback we rely on', () => {
    // Deliberately not an equality assertion against the backend's chain list.
    // Entries here are optional enrichment, so a chain rotki gains does not have
    // to appear, and adding a new entry must not fail a test.
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
