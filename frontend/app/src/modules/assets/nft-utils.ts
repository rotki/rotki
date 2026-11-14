export function isNft(address?: string): boolean {
  if (!address)
    return false;

  return address.startsWith('_nft_');
}

/** Whether an identifier belongs to an ERC721 token or a Solana SPL NFT. */
export function isErc721OrSolanaNft(identifier?: string): boolean {
  if (!identifier)
    return false;

  return (
    (identifier.startsWith('eip155:') && identifier.includes('/erc721:'))
    || identifier.startsWith('solana/nft:')
  );
}

/** Whether an identifier represents any non-fungible asset format supported by rotki. */
export function isNonFungible(identifier?: string): boolean {
  return isNft(identifier) || isErc721OrSolanaNft(identifier);
}
