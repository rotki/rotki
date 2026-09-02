import type { SupportedAsset } from '@rotki/common';
import type { Collection } from '@/modules/core/common/collection';
import { describe, expect, it } from 'vitest';
import { CUSTOM_ASSET } from '@/modules/assets/types';
import { useAssetDisplayHelpers } from './use-asset-display-helpers';

const EVM_IDENTIFIER = 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F';

function asset(overrides: Partial<SupportedAsset> = {}): SupportedAsset {
  return { identifier: 'ETH', isRebasing: false, ...overrides };
}

function collection(data: SupportedAsset[]): Collection<SupportedAsset> {
  return { data, found: data.length, limit: -1, total: data.length };
}

const nothingWhitelisted = (): boolean => false;

function helpers(
  data: SupportedAsset[] = [],
  isAssetWhitelisted: (identifier: string) => boolean = nothingWhitelisted,
): ReturnType<typeof useAssetDisplayHelpers> {
  return useAssetDisplayHelpers(collection(data), isAssetWhitelisted);
}

describe('modules/assets/admin/useAssetDisplayHelpers', () => {
  describe('formatType', () => {
    it('should sentence-case the given type', () => {
      expect(helpers().formatType('evm token')).toBe('Evm token');
    });

    it('should fall back to an EVM token for a missing type', () => {
      expect(helpers().formatType()).toBe('EVM token');
      expect(helpers().formatType(null)).toBe('EVM token');
    });

    it('should leave an empty type empty, unlike a null one, so the column renders blank', () => {
      expect(helpers().formatType('')).toBe('');
    });
  });

  describe('the display name', () => {
    it('should prefer the name', () => {
      const display = helpers().getAsset(asset({ name: 'Dai', symbol: 'DAI' }));

      expect(display.name).toBe('Dai');
    });

    it('should fall back to the symbol when there is no name', () => {
      const display = helpers().getAsset(asset({ name: null, symbol: 'DAI' }));

      expect(display.name).toBe('DAI');
    });

    it('should fall back to the contract address for an evm asset with neither', () => {
      const display = helpers().getAsset(asset({ identifier: EVM_IDENTIFIER, name: null, symbol: null }));

      expect(display.name).toBe('0x6B175474E89094C44Da98b954EedeAC495271d0F');
    });

    it('should fall back to the identifier when it is not an evm asset', () => {
      const display = helpers().getAsset(asset({ identifier: 'BTC', name: null, symbol: null }));

      expect(display.name).toBe('BTC');
    });
  });

  describe('getAsset', () => {
    it('should carry the identifier, chain and protocol through', () => {
      const display = helpers().getAsset(asset({
        evmChain: 'ethereum',
        identifier: EVM_IDENTIFIER,
        protocol: 'spam',
      }));

      expect(display.identifier).toBe(EVM_IDENTIFIER);
      expect(display.evmChain).toBe('ethereum');
      expect(display.protocol).toBe('spam');
    });

    it('should default an absent symbol and custom type to empty strings', () => {
      const display = helpers().getAsset(asset({ customAssetType: null, symbol: null }));

      expect(display.symbol).toBe('');
      expect(display.customAssetType).toBe('');
    });

    it('should flag a custom asset', () => {
      expect(helpers().getAsset(asset({ assetType: CUSTOM_ASSET })).isCustomAsset).toBe(true);
      expect(helpers().getAsset(asset({ assetType: 'evm token' })).isCustomAsset).toBe(false);
    });
  });

  describe('what a row allows', () => {
    it('should allow editing and ignoring a regular asset', () => {
      const regular = asset({ assetType: 'evm token' });

      expect(helpers().canBeEdited(regular)).toBe(true);
      expect(helpers().canBeIgnored(regular)).toBe(true);
    });

    it('should allow neither for a custom asset', () => {
      const custom = asset({ assetType: CUSTOM_ASSET });

      expect(helpers().canBeEdited(custom)).toBe(false);
      expect(helpers().canBeIgnored(custom)).toBe(false);
    });
  });

  describe('the disabled rows', () => {
    it('should disable a spam asset', () => {
      const rows = [asset({ identifier: 'SPAM', protocol: 'spam' }), asset({ identifier: 'ETH' })];

      expect(get(helpers(rows).disabledRows).map(item => item.identifier)).toEqual(['SPAM']);
    });

    it('should disable a whitelisted asset', () => {
      const rows = [asset({ identifier: 'SAFE' }), asset({ identifier: 'ETH' })];

      const disabled = get(helpers(rows, identifier => identifier === 'SAFE').disabledRows);

      expect(disabled.map(item => item.identifier)).toEqual(['SAFE']);
    });

    it('should disable a row that is both, listing it once', () => {
      const rows = [asset({ identifier: 'SAFE', protocol: 'spam' })];

      const disabled = get(helpers(rows, identifier => identifier === 'SAFE').disabledRows);

      expect(disabled).toHaveLength(1);
    });

    it('should disable nothing when neither applies', () => {
      const rows = [asset({ identifier: 'ETH' }), asset({ identifier: 'BTC' })];

      expect(get(helpers(rows).disabledRows)).toEqual([]);
    });

    it('should not treat another protocol as spam', () => {
      const rows = [asset({ identifier: 'AAVE', protocol: 'aave' })];

      expect(get(helpers(rows).disabledRows)).toEqual([]);
    });
  });
});
