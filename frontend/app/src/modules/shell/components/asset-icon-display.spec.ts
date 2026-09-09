import { type AssetInfoWithId, Blockchain } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { HYPERLIQUID_TOKEN, SOLANA_CHAIN, SOLANA_TOKEN } from '@/modules/assets/types';
import {
  assetChain,
  assetTooltip,
  badgeSize,
  displayAssetText,
  visibleProtocol,
} from '@/modules/shell/components/asset-icon-display';

function asset(overrides: Partial<AssetInfoWithId> = {}): AssetInfoWithId {
  return { identifier: 'ETH', isCustomAsset: false, name: 'Ethereum', symbol: 'ETH', ...overrides };
}

describe('assetChain', () => {
  it('should take an evm asset chain from the asset', () => {
    expect(assetChain(undefined, asset({ evmChain: 'optimism' }))).toBe('optimism');
  });

  /** Solana and hyperliquid tokens carry no chain, and are recognised by their type instead. */
  it('should recognise a solana token by its type', () => {
    expect(assetChain(undefined, asset({ assetType: SOLANA_TOKEN }))).toBe(SOLANA_CHAIN);
  });

  it('should recognise a hyperliquid token by its type', () => {
    expect(assetChain(undefined, asset({ assetType: HYPERLIQUID_TOKEN }))).toBe(Blockchain.HYPERLIQUID);
  });

  it('should badge nothing for an asset with no chain', () => {
    expect(assetChain(undefined, asset())).toBeUndefined();
  });

  it('should badge nothing while the asset is still resolving', () => {
    expect(assetChain(undefined, null)).toBeUndefined();
  });

  describe('a chain the caller forces', () => {
    it('should win over the asset own chain', () => {
      expect(assetChain('base', asset({ evmChain: 'optimism' }))).toBe('base');
    });

    it('should show even before the asset resolves', () => {
      expect(assetChain('base', null)).toBe('base');
    });
  });
});

describe('visibleProtocol', () => {
  it('should badge a real protocol', () => {
    expect(visibleProtocol('aave')).toBe('aave');
  });

  /** Spam is a classification, and badging it would dress a spam token as a real one. */
  it('should not badge spam as a protocol', () => {
    expect(visibleProtocol('spam')).toBeUndefined();
  });

  it('should badge nothing when the asset has no protocol', () => {
    expect(visibleProtocol(undefined)).toBeUndefined();
  });

  it('should badge nothing for an empty protocol', () => {
    expect(visibleProtocol('')).toBeUndefined();
  });
});

describe('displayAssetText', () => {
  /** A fiat currency shows its own symbol, which is why it outranks the asset's names. */
  it('should prefer the currency symbol', () => {
    expect(displayAssetText('$', 'USD', 'US Dollar', 'USD')).toBe('$');
  });

  it('should fall back to the symbol', () => {
    expect(displayAssetText(undefined, 'ETH', 'Ethereum', 'eip155:1/erc20:0x0')).toBe('ETH');
  });

  it('should fall back to the name when there is no symbol', () => {
    expect(displayAssetText(undefined, undefined, 'Ethereum', 'eip155:1/erc20:0x0')).toBe('Ethereum');
  });

  it('should fall back to the identifier when the asset has neither', () => {
    expect(displayAssetText(undefined, undefined, undefined, 'eip155:1/erc20:0x0')).toBe('eip155:1/erc20:0x0');
  });

  it('should never be undefined', () => {
    expect(displayAssetText(undefined, undefined, undefined, undefined)).toBe('');
  });
});

describe('assetTooltip', () => {
  it('should show both when they differ', () => {
    expect(assetTooltip('Ethereum', 'ETH', false)).toEqual({ name: 'Ethereum', symbol: 'ETH' });
  });

  /** Repeating the symbol as a name would render `[ETH] ETH`. */
  it('should drop a name that only repeats the symbol', () => {
    expect(assetTooltip('ETH', 'ETH', false)).toEqual({ name: '', symbol: 'ETH' });
  });

  it('should treat a case difference as a repeat', () => {
    expect(assetTooltip('eth', 'ETH', false)).toEqual({ name: '', symbol: 'ETH' });
  });

  /** A custom asset has no symbol of its own, so its name is what the tooltip shows as one. */
  it('should show a custom asset name as the symbol', () => {
    expect(assetTooltip('My holdings', '', true)).toEqual({ name: '', symbol: 'My holdings' });
  });

  it('should show a custom asset name even when a symbol exists', () => {
    expect(assetTooltip('My holdings', 'MINE', true)).toEqual({ name: '', symbol: 'My holdings' });
  });

  it('should render an unresolved asset as two empty strings', () => {
    expect(assetTooltip(undefined, undefined, false)).toEqual({ name: '', symbol: '' });
  });
});

describe('badgeSize', () => {
  it('should take half the icon for a chain badge', () => {
    expect(badgeSize(undefined, '24px', 50)).toBe('12px');
  });

  it('should take two fifths for a protocol badge', () => {
    expect(badgeSize(undefined, '40px', 40)).toBe('16px');
  });

  it('should read the size from a css length', () => {
    expect(badgeSize(undefined, '24', 50)).toBe('12px');
  });

  /** An explicit size is the caller overriding the scale deliberately. */
  it('should let the caller override it', () => {
    expect(badgeSize('9px', '24px', 50)).toBe('9px');
  });
});
