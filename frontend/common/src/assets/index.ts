import { EvmTokenKind } from '../data';
import { isValidEthAddress, isValidSolanaAddress } from '../text';

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

export function isEvmIdentifierWithNftId(identifier?: string): boolean {
  if (!identifier)
    return false;

  // Check if it's a valid EVM identifier format (eip155:chainId/erc721:address/nftId)
  // by temporarily removing the /nftId suffix
  const { address, nftId } = getAddressAndNftIdFromIdentifier(identifier);
  if (!nftId || !/^\d+$/.test(nftId))
    return false;

  // Reconstruct without the nftId to validate as a standard EVM identifier
  const parts = identifier.split(':');
  if (parts.length !== 3)
    return false;

  const baseIdentifier = `${parts[0]}:${parts[1]}:${address}`;

  // Check if base format is valid and protocol is erc721
  if (!isEvmIdentifier(baseIdentifier))
    return false;

  const protocol = parts[1]?.split('/')[1];
  return protocol === 'erc721';
}

export function getNftAssetIdDetail(identifier?: string): { contractAddress: string; nftId: string } | undefined {
  if (!identifier || !isEvmIdentifierWithNftId(identifier)) {
    return { contractAddress: '', nftId: '' };
  }

  const { address, nftId } = getAddressAndNftIdFromIdentifier(identifier);

  return {
    contractAddress: address,
    nftId,
  };
}

export function isSolanaTokenIdentifier(identifier?: string): boolean {
  if (!identifier)
    return false;

  const parts = identifier.split(':');
  if (parts.length !== 2)
    return false;

  if (!parts[0] || parts[0] !== 'solana/token')
    return false;

  const address = parts[1];
  return !(!address || !isValidSolanaAddress(address));
}

export function getAddressFromEvmIdentifier(identifier?: string): string {
  if (!identifier)
    return '';

  return identifier.split(':')[2] ?? '';
}

function getAddressAndNftIdFromIdentifier(identifier: string): { address: string; nftId: string } {
  const addressAndId = identifier.split(':')[2];
  const addressParts = addressAndId?.split('/') ?? [];
  return {
    address: addressParts[0] ?? '',
    nftId: addressParts[1] ?? '',
  };
}

export function createEvmIdentifierFromAddress(address: string, chain = '1'): string {
  return `eip155:${chain}/erc20:${address}`;
}

export function getValidSelectorFromEvmAddress(address: string): string {
  return address.replace(/[^\da-z]/gi, '');
}

export function getAddressFromSolanaIdentifier(identifier?: string): string {
  if (!identifier)
    return '';

  return identifier.split(':')[1] ?? '';
}
