import { EvmTokenKind, type SupportedAsset } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { managedAssetSchema, toManagedAssetFormState } from '@/modules/assets/admin/managed/managed-asset-form';
import { CUSTOM_ASSET, EVM_TOKEN, HYPERLIQUID_TOKEN, SOLANA_TOKEN } from '@/modules/assets/types';

const messages = {
  addressInvalid: 'address_invalid',
  addressMissing: 'address_missing',
  assetTypeMissing: 'type_missing',
  collectibleIdMissing: 'collectible_missing',
};

const EVM_ADDRESS = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
const SOLANA_ADDRESS = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const HYPERLIQUID_ADDRESS = '0x0d01dc56dcaaca66ad901c959b4011ec';

const token = {
  address: EVM_ADDRESS,
  assetType: EVM_TOKEN,
  identifier: 'test-asset',
  name: 'USD Coin',
};

function messagesFor(
  state: Record<string, unknown>,
  rules = { isNft: false, requiresAddress: true },
): string[] {
  const result = managedAssetSchema(messages, rules).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.message);
}

describe('managedAssetSchema', () => {
  it('should accept a filled token', () => {
    expect(messagesFor(token)).toEqual([]);
  });

  it('should report a missing asset type', () => {
    expect(messagesFor({ ...token, assetType: '' })).toEqual(['type_missing']);
  });

  it('should report a missing address as missing and nothing else', () => {
    // Vuelidate reported this as both missing and malformed. Saying an empty field is the wrong
    // shape adds nothing to being told it is empty.
    expect(messagesFor({ ...token, address: '' })).toEqual(['address_missing']);
  });

  it.each([
    [EVM_TOKEN, SOLANA_ADDRESS],
    [SOLANA_TOKEN, EVM_ADDRESS],
    [HYPERLIQUID_TOKEN, SOLANA_ADDRESS],
  ])('should reject an address that is not %s shaped', (assetType, address) => {
    expect(messagesFor({ ...token, address, assetType })).toEqual(['address_invalid']);
  });

  it.each([
    [EVM_TOKEN, EVM_ADDRESS],
    [SOLANA_TOKEN, SOLANA_ADDRESS],
    [HYPERLIQUID_TOKEN, HYPERLIQUID_ADDRESS],
  ])('should accept the address %s spells', (assetType, address) => {
    expect(messagesFor({ ...token, address, assetType })).toEqual([]);
  });

  it('should not ask an asset with no address for one', () => {
    const rules = { isNft: false, requiresAddress: false };

    expect(messagesFor({ assetType: CUSTOM_ASSET, identifier: 'x' }, rules)).toEqual([]);
  });

  it('should not check the shape of an address it does not require', () => {
    const rules = { isNft: false, requiresAddress: false };

    expect(messagesFor({ ...token, address: 'nonsense', assetType: CUSTOM_ASSET }, rules)).toEqual([]);
  });

  it('should require a collectible id from an nft', () => {
    const rules = { isNft: true, requiresAddress: true };

    expect(messagesFor({ ...token, collectibleId: '' }, rules)).toEqual(['collectible_missing']);
  });

  it('should not ask a fungible token for a collectible id', () => {
    expect(messagesFor({ ...token, collectibleId: '' })).toEqual([]);
  });

  it.each([
    ['coingecko'],
    ['cryptocompare'],
    ['protocol'],
    ['symbol'],
    ['name'],
    ['decimals'],
  ])('should carry %s without validating it', (key) => {
    // These are where server errors land, not rules. A structural rule here would block the save
    // with nothing on screen, since most of them show no message of their own.
    expect(messagesFor({ ...token, [key]: '' })).toEqual([]);
  });

  it('should carry the fields it does not validate', () => {
    const result = managedAssetSchema(messages, { isNft: false, requiresAddress: true })
      .safeParse({ ...token, decimals: 6, underlyingTokens: [] });

    expect(result.success && result.data).toEqual({ ...token, decimals: 6, underlyingTokens: [] });
  });
});

describe('toManagedAssetFormState', () => {
  const asset: SupportedAsset = {
    address: EVM_ADDRESS,
    assetType: EVM_TOKEN,
    identifier: 'test-asset',
    isRebasing: false,
  };

  it('should open an unset optional field as an empty string', () => {
    const state = toManagedAssetFormState(asset);

    // The inputs need something to write into, and null is not it.
    expect(state.name).toBe('');
    expect(state.symbol).toBe('');
    expect(state.coingecko).toBe('');
    expect(state.collectibleId).toBe('');
    expect(state.forked).toBe('');
  });

  it('should keep the value an optional field already has', () => {
    const state = toManagedAssetFormState({ ...asset, name: 'USD Coin', protocol: 'aave' });

    expect(state.name).toBe('USD Coin');
    expect(state.protocol).toBe('aave');
  });

  it('should leave the fields with their own converters alone', () => {
    // `decimals` and `started` keep the difference between unset and zero, which the payload
    // records as null and their converters read on the way to the input.
    const state = toManagedAssetFormState(asset);

    expect(state.decimals).toBeUndefined();
    expect(state.started).toBeUndefined();
  });

  it('should carry the rest of the payload through untouched', () => {
    const state = toManagedAssetFormState({ ...asset, decimals: 6, ended: 42, tokenKind: EvmTokenKind.ERC20 });

    expect(state.identifier).toBe('test-asset');
    expect(state.decimals).toBe(6);
    expect(state.ended).toBe(42);
    expect(state.tokenKind).toBe(EvmTokenKind.ERC20);
  });

  // The mirroring in `useMappedModelForm` compares the mapped payload against the state to decide
  // whether an outside edit is news. A mapper that answered differently for the same input would
  // report every pass as a change and the two directions would never settle.
  it('should answer the same for the same payload', () => {
    expect(toManagedAssetFormState(asset)).toEqual(toManagedAssetFormState(asset));
  });
});
