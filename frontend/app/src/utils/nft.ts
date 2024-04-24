export function isNft(address?: string): boolean {
  if (!address)
    return false;

  return address.startsWith('_nft_');
}
