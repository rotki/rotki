import { EvmTokenKind } from '../data';
import { isValidEthAddress, isValidHyperliquidTokenAddress, isValidSolanaAddress } from '../text';

const HYPERLIQUID_TOKEN_IDENTIFIER_PREFIX = 'hyperc:';

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

/**
 * Whether an identifier is an EVM one carrying an nft id, as `eip155:1/erc721:0xabc/42`.
 *
 * @remarks
 * Checked by stripping the `/nftId` suffix and validating what remains as a standard EVM
 * identifier, so the two halves cannot drift apart.
 */
export function isEvmIdentifierWithNftId(identifier?: string): boolean {
  if (!identifier)
    return false;

  const { address, nftId } = getAddressAndNftIdFromIdentifier(identifier);
  if (!nftId || !/^\d+$/.test(nftId))
    return false;

  const parts = identifier.split(':');
  if (parts.length !== 3)
    return false;

  const withoutNftId = `${parts[0]}:${parts[1]}:${address}`;
  if (!isEvmIdentifier(withoutNftId))
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

export function getChainIdFromEvmIdentifier(identifier?: string): number | undefined {
  if (!identifier || !isEvmIdentifier(identifier))
    return undefined;

  const chainId = Number.parseInt(identifier.split(':')[1].split('/')[0]);
  return Number.isNaN(chainId) ? undefined : chainId;
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

/** Checks whether an identifier contains a valid Hyperliquid Core token address. */
export function isHyperliquidTokenIdentifier(identifier?: string): boolean {
  if (!identifier)
    return false;

  return identifier.startsWith(HYPERLIQUID_TOKEN_IDENTIFIER_PREFIX)
    && isValidHyperliquidTokenAddress(identifier.slice(HYPERLIQUID_TOKEN_IDENTIFIER_PREFIX.length));
}

/** Extracts and normalizes the address from a Hyperliquid Core token identifier. */
export function getAddressFromHyperliquidTokenIdentifier(identifier?: string): string {
  if (!identifier || !isHyperliquidTokenIdentifier(identifier))
    return '';

  return identifier.slice(HYPERLIQUID_TOKEN_IDENTIFIER_PREFIX.length).toLowerCase();
}
