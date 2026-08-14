import type { ManagedAssetPayload } from '@/modules/assets/api/use-asset-management-api';
import { EvmTokenKind, type SupportedAsset } from '@rotki/common';
import { HYPERLIQUID_TOKEN_ADDRESS } from '@test/utils/asset-test-data';
import { describe, expect, it } from 'vitest';
import { CUSTOM_ASSET, EVM_TOKEN, HYPERLIQUID_TOKEN, SOLANA_TOKEN } from '@/modules/assets/types';
import { buildManagedAssetPayload, prepareNonEvmAssetPayload } from './managed-asset-payload';

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

describe('buildManagedAssetPayload', () => {
  const evmToken = (overrides: Partial<SupportedAsset> = {}): SupportedAsset => ({
    address: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    assetType: EVM_TOKEN,
    decimals: 6,
    evmChain: 'ethereum',
    identifier: 'test-asset',
    isRebasing: false,
    name: 'USD Coin',
    symbol: 'USDC',
    tokenKind: EvmTokenKind.ERC20,
    ...overrides,
  });

  it('should drop the fields the form only carries', () => {
    const payload = buildManagedAssetPayload(evmToken({
      active: true,
      customAssetType: 'real estate',
      ended: 1600000000,
    }), []);

    expect(payload).not.toHaveProperty('active');
    expect(payload).not.toHaveProperty('ended');
    expect(payload).not.toHaveProperty('customAssetType');
  });

  it.each([
    ['forked'],
    ['protocol'],
    ['swappedFor'],
  ] as const)('should send no %s rather than an empty one', (key) => {
    const payload = buildManagedAssetPayload(evmToken({ [key]: '' }), []);

    expect(payload[key]).toBeUndefined();
  });

  it('should keep those fields when they hold something', () => {
    const payload = buildManagedAssetPayload(evmToken({
      forked: 'ETC',
      protocol: 'uniswap-v3',
      swappedFor: 'DAI',
    }), []);

    expect(payload).toMatchObject({ forked: 'ETC', protocol: 'uniswap-v3', swappedFor: 'DAI' });
  });

  it('should send empty oracle identifiers as empty strings', () => {
    // The api reads an empty string here as "no identifier", and the form has no way to express
    // the difference, so both absent and cleared arrive the same way.
    const payload = buildManagedAssetPayload(evmToken(), []);

    expect(payload).toMatchObject({ coingecko: '', cryptocompare: '' });
  });

  it('should null an empty chain and token kind', () => {
    const payload = buildManagedAssetPayload(evmToken({ evmChain: '', tokenKind: undefined }), []);

    expect(payload).toMatchObject({ evmChain: null, tokenKind: null });
  });

  it('should carry underlying tokens only when there are some', () => {
    const token = {
      address: '0x6B175474E89094C44Da98b954EedeAC495271d0F',
      tokenKind: EvmTokenKind.ERC20,
      weight: '100',
    };

    expect(buildManagedAssetPayload(evmToken(), [token]).underlyingTokens).toEqual([token]);
    expect(buildManagedAssetPayload(evmToken(), []).underlyingTokens).toBeUndefined();
  });

  it('should drop the collectible id from a fungible token', () => {
    const payload = buildManagedAssetPayload(evmToken({ collectibleId: '42' }), []);

    expect(payload).not.toHaveProperty('collectibleId');
  });

  it('should keep the collectible id of an nft, which cannot rebase', () => {
    const payload = buildManagedAssetPayload(
      evmToken({ collectibleId: '42', isRebasing: true, tokenKind: EvmTokenKind.ERC721 }),
      [],
    );

    expect(payload).toMatchObject({ collectibleId: '42', isRebasing: false });
  });

  it('should reshape a non-evm asset and stop it rebasing', () => {
    const payload = buildManagedAssetPayload(evmToken({
      assetType: SOLANA_TOKEN,
      collectibleId: '42',
      isRebasing: true,
    }), []);

    expect(payload).toMatchObject({ assetType: SOLANA_TOKEN, isRebasing: false });
    // prepareNonEvmAssetPayload owns which fields survive; this only pins that it ran.
    expect(payload).not.toHaveProperty('collectibleId');
    expect(payload).not.toHaveProperty('evmChain');
  });
});
