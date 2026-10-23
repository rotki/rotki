import { describe, expect, it } from 'vitest';
import {
  assetExportActivity,
  assetImportActivity,
  assetResetActivity,
  assetUpdateActivity,
  assetVersionsActivity,
  erc20InfoActivity,
  nftAssetsActivity,
} from '@/modules/assets/assets.activity';

const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

/**
 * The ids are asserted as literals on purpose, as in `decode.activity.spec.ts`: comparing a
 * descriptor against itself holds whatever it produces, so a changed id shape would pass while the
 * readers that ask by it silently stopped matching.
 */
describe('asset activity ids', () => {
  it('should give each database operation its fixed id', () => {
    expect(assetVersionsActivity.id()).toBe('assets:versions');
    expect(assetUpdateActivity.id()).toBe('assets:update');
    expect(assetImportActivity.id()).toBe('assets:import');
    expect(assetExportActivity.id()).toBe('assets:export');
    expect(assetResetActivity.id()).toBe('assets:reset');
  });

  it('should key a token lookup by chain and address', () => {
    expect(erc20InfoActivity.id({ address, evmChain: 'ethereum' })).toBe(`assets:erc20:ethereum:${address}`);
  });

  it('should give one address on two chains distinct lookups, so neither joins the other', () => {
    expect(erc20InfoActivity.id({ address, evmChain: 'ethereum' }))
      .not
      .toBe(erc20InfoActivity.id({ address, evmChain: 'optimism' }));
  });

  it('should cancel a timed-out lookup by the same parts it was submitted under', () => {
    const subject = { address, evmChain: 'ethereum' };
    expect(erc20InfoActivity.partsOf(subject)).toStrictEqual(['erc20', 'ethereum', address]);
  });

  it('should key the NFT list by the cache flag, so a forced fetch never joins a cached one', () => {
    expect(nftAssetsActivity.id({ ignoreCache: false })).toBe('assets:nfts:cached');
    expect(nftAssetsActivity.id({ ignoreCache: true })).toBe('assets:nfts:pull');
  });
});
