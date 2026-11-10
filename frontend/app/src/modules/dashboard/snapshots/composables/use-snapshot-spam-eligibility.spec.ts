import type { ComputedRef } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import { SnapshotSpamEligibility, useSnapshotSpamEligibility } from '@/modules/dashboard/snapshots/composables/use-snapshot-spam-eligibility';

const TOKEN = 'eip155:1/erc20:0xfcaF0e4498E78d65526a507360F755178b804Ba8';
const SPAM_TOKEN = 'eip155:1/erc20:0x6982508145454Ce325dDbE47a25d4ec3d2311933';
const IGNORED_TOKEN = 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F';
const MANUAL_TOKEN = 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
const SOLANA_TOKEN = 'solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';

vi.mock('@/modules/dashboard/snapshots/composables/use-snapshot-asset-filters', () => ({
  useSnapshotAssetFilters: (): { isIgnoredAsset: (id: string) => boolean } => ({
    isIgnoredAsset: (id: string): boolean => id === IGNORED_TOKEN || id === SPAM_TOKEN,
  }),
}));

vi.mock('@/modules/balances/manual/use-manual-balance-data', async () => {
  const { computed } = await import('vue');
  return {
    useManualBalanceData: (): { manualBalancesAssets: ComputedRef<string[]> } => ({
      manualBalancesAssets: computed<string[]>(() => [MANUAL_TOKEN]),
    }),
  };
});

describe('modules/dashboard/snapshots/composables/use-snapshot-spam-eligibility', () => {
  const { spamEligibility } = useSnapshotSpamEligibility();

  it('should offer an EVM token that is neither spam, ignored nor in a manual balance', () => {
    expect(spamEligibility(TOKEN)).toBe(SnapshotSpamEligibility.ELIGIBLE);
  });

  it('should refuse a native asset, a Solana token, an NFT and a custom asset', () => {
    for (const asset of ['ETH', SOLANA_TOKEN, '_nft_0xabc_1', 'a1b2c3d4-custom'])
      expect(spamEligibility(asset)).toBe(SnapshotSpamEligibility.UNAVAILABLE);
  });

  it('should refuse a token that is already spam or ignored', () => {
    expect(spamEligibility(SPAM_TOKEN)).toBe(SnapshotSpamEligibility.UNAVAILABLE);
    expect(spamEligibility(IGNORED_TOKEN)).toBe(SnapshotSpamEligibility.UNAVAILABLE);
  });

  it('should hold back a token used in a manual balance', () => {
    expect(spamEligibility(MANUAL_TOKEN)).toBe(SnapshotSpamEligibility.MANUAL_BALANCE);
  });
});
