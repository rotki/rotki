import { EvmTokenKind } from '../data';
import { isValidEthAddress } from '../text';

export function isEvmIdentifier(identifier?: string): boolean {
  if (!identifier)
    return false;

  const parts = identifier.split(':');
  if (parts.length !== 3)
    return false;

  if (!parts[0] || parts[0] !== 'eip155')
    return false;

  const chainAndProtocol = parts[1].split('/');
  if (chainAndProtocol.length !== 2)
    return false;

  const chainId = chainAndProtocol[0];
  if (!chainId || !/^\d+$/.test(chainId))
    return false;

  const protocol = chainAndProtocol[1];
  if (!Object.values(EvmTokenKind).map(item => item.toString()).includes(protocol)) {
    return false;
  }

  const address = parts[2];
  return !(!address || !isValidEthAddress(address));
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
