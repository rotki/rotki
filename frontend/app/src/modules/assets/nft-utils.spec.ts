import { describe, expect, it } from 'vitest';
import { isErc721OrSolanaNft, isNft, isNonFungible } from '@/modules/assets/nft-utils';

describe('nFT identifier utilities', () => {
  it.each([
    '_nft_0x123_1',
    'eip155:1/erc721:0x123/1',
    'eip155:137/erc721:0x456/2',
    'solana/nft:Mint111',
  ])('should classify %s as non-fungible', (identifier) => {
    expect(isNonFungible(identifier)).toBe(true);
  });

  it.each([
    'eip155:1/erc20:0x123',
    'other_chain/erc721:not_an_evm_nft',
    'solana/token:Mint111',
  ])('should not classify %s as non-fungible', (identifier) => {
    expect(isNonFungible(identifier)).toBe(false);
  });

  it('should preserve the legacy NFT-module distinction', () => {
    expect(isNft('_nft_0x123_1')).toBe(true);
    expect(isNft('eip155:1/erc721:0x123/1')).toBe(false);
    expect(isErc721OrSolanaNft('_nft_0x123_1')).toBe(false);
  });
});
