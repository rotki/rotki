export function isEvmIdentifier(identifier?: string): boolean {
  if (!identifier)
    return false;

  return identifier.startsWith('eip155');
}

export function getAddressFromEvmIdentifier(identifier?: string): string {
  if (!identifier)
    return '';

  return identifier.split(':')[2] ?? '';
}

export function createEvmIdentifierFromAddress(address: string, chain = '1'): string {
  return `eip155:${chain}/erc20:${address}`;
}

export function getValidSelectorFromEvmAddress(address: string): string {
  return address.replace(/[^\da-z]/gi, '');
}
