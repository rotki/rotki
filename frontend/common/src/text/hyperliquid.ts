/** Checks whether an address is a 16-byte Hyperliquid Core token identifier. */
export function isValidHyperliquidTokenAddress(address?: string): boolean {
  if (!address)
    return false;

  return /^0x[\dA-Fa-f]{32}$/.test(address);
}
