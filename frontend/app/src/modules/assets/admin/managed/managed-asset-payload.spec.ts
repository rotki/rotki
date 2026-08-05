import type { ManagedAssetPayload } from '@/modules/assets/api/use-asset-management-api';
import { EvmTokenKind } from '@rotki/common';
import { HYPERLIQUID_TOKEN_ADDRESS } from '@test/utils/asset-test-data';
import { describe, expect, it } from 'vitest';
import { CUSTOM_ASSET, HYPERLIQUID_TOKEN, SOLANA_TOKEN } from '@/modules/assets/types';
import { prepareNonEvmAssetPayload } from './managed-asset-payload';

describe('prepareNonEvmAssetPayload', () => {
  it('should retain Solana token fields and omit EVM-only fields', () => {
    const payload: ManagedAssetPayload = {
      address: 'solana-address',
      assetType: SOLANA_TOKEN,
      collectibleId: '42',
      decimals: 6,
      evmChain: 'ethereum',
      identifier: 'test-asset',
      protocol: 'uniswap-v3',
      tokenKind: EvmTokenKind.ERC721,
      underlyingTokens: [],
    };

    expect(prepareNonEvmAssetPayload(payload)).toEqual({
      address: 'solana-address',
      assetType: SOLANA_TOKEN,
      decimals: 6,
      identifier: 'test-asset',
      protocol: 'uniswap-v3',
      tokenKind: EvmTokenKind.ERC721,
    });
  });

  it('should retain Hyperliquid token data, normalize its address, and omit unsupported fields', () => {
    const payload: ManagedAssetPayload = {
      address: HYPERLIQUID_TOKEN_ADDRESS.toUpperCase().replace('0X', '0x'),
      assetType: HYPERLIQUID_TOKEN,
      collectibleId: '42',
      decimals: 6,
      evmChain: 'ethereum',
      identifier: 'test-asset',
      protocol: 'uniswap-v3',
      tokenKind: EvmTokenKind.ERC20,
      underlyingTokens: [],
    };

    expect(prepareNonEvmAssetPayload(payload)).toEqual({
      address: HYPERLIQUID_TOKEN_ADDRESS,
      assetType: HYPERLIQUID_TOKEN,
      decimals: 6,
      identifier: 'test-asset',
    });
  });

  it('should omit all token fields from custom asset payloads', () => {
    const payload: ManagedAssetPayload = {
      address: HYPERLIQUID_TOKEN_ADDRESS,
      assetType: CUSTOM_ASSET,
      collectibleId: '42',
      decimals: 6,
      evmChain: 'ethereum',
      identifier: 'test-asset',
      tokenKind: EvmTokenKind.ERC721,
      underlyingTokens: [],
    };

    expect(prepareNonEvmAssetPayload(payload)).toEqual({
      assetType: CUSTOM_ASSET,
      identifier: 'test-asset',
    });
  });
});
