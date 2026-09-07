import type { SupportedAsset } from '@rotki/common';
import type { TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/modules/core/common/collection';
import { createMock } from '@test/utils/create-mock';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref } from 'vue';
import { EVM_TOKEN, SOLANA_CHAIN, SOLANA_TOKEN } from '@/modules/assets/types';
import { useManagedAssetTable } from './use-managed-asset-table';

let itemsPerPage: Ref<number>;

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<number> => itemsPerPage,
}));

function asset(overrides: Partial<SupportedAsset> = {}): SupportedAsset {
  return createMock<SupportedAsset>({
    assetType: 'own chain',
    identifier: 'BTC',
    ...overrides,
  });
}

function page(data: SupportedAsset[], found = data.length): Collection<SupportedAsset> {
  return { data, found, limit: -1, total: found, totalValue: undefined };
}

let pagination: Ref<TablePaginationData>;
let expanded: Ref<SupportedAsset[]>;
let collection: Ref<Collection<SupportedAsset>>;
let selected: Ref<string[]>;
let scope: ReturnType<typeof effectScope>;

function table(): ReturnType<typeof useManagedAssetTable> {
  scope = effectScope();
  return scope.run(() => useManagedAssetTable(pagination, expanded, collection, selected))!;
}

describe('modules/assets/admin/useManagedAssetTable', () => {
  beforeEach(() => {
    itemsPerPage = ref<number>(10);
    pagination = ref<TablePaginationData>({ limit: 10, page: 1, total: 0 });
    expanded = ref<SupportedAsset[]>([]);
    collection = ref<Collection<SupportedAsset>>(page([]));
    selected = ref<string[]>([]);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the rows', () => {
    it('should read them from the collection', () => {
      set(collection, page([asset({ identifier: 'BTC' })]));

      const { data } = table();

      expect(get(data)).toHaveLength(1);
    });
  });

  describe('the columns', () => {
    it('should offer the asset, its type, address and start alongside the row controls', () => {
      const { cols } = table();

      expect(get(cols).map(col => col.key)).toContain('symbol');
      expect(get(cols).map(col => col.key)).toEqual(
        expect.arrayContaining(['symbol', 'type', 'address', 'started']),
      );
    });
  });

  describe('expanding a row', () => {
    it('should keep only one row open at a time', () => {
      const { expand, isExpanded } = table();
      expand(asset({ identifier: 'BTC' }));
      expand(asset({ identifier: 'ETH' }));

      expect(isExpanded('BTC')).toBe(false);
      expect(isExpanded('ETH')).toBe(true);
    });

    it('should collapse a row that is already expanded', () => {
      const { expand, isExpanded } = table();
      expand(asset({ identifier: 'BTC' }));
      expand(asset({ identifier: 'BTC' }));

      expect(isExpanded('BTC')).toBe(false);
    });
  });

  describe('falling back to the last page', () => {
    it('should step back when the page it is on has emptied', async () => {
      table();
      set(collection, page([], 25));
      await flushPromises();

      expect(get(pagination).page).toBe(3);
    });

    it('should stay put while the page still holds rows', async () => {
      table();
      set(collection, page([asset()], 25));
      await flushPromises();

      expect(get(pagination).page).toBe(1);
    });

    it('should stay put when there is nothing at all', async () => {
      table();
      set(collection, page([], 0));
      await flushPromises();

      expect(get(pagination).page).toBe(1);
    });
  });

  describe('whether the selection can be marked as spam', () => {
    it('should stay available while nothing is selected', () => {
      set(collection, page([asset({ assetType: 'own chain', identifier: 'BTC' })]));

      const { spamDisabled } = table();

      expect(get(spamDisabled)).toBe(false);
    });

    it('should be available when a selected asset is of a spammable type', () => {
      set(collection, page([asset({ assetType: EVM_TOKEN, identifier: 'eip155:1/erc20:0xABC' })]));
      set(selected, ['eip155:1/erc20:0xABC']);

      const { spamDisabled } = table();

      expect(get(spamDisabled)).toBe(false);
    });

    it('should be unavailable when no selected asset can be spam', () => {
      set(collection, page([asset({ assetType: 'own chain', identifier: 'BTC' })]));
      set(selected, ['BTC']);

      const { spamDisabled } = table();

      expect(get(spamDisabled)).toBe(true);
    });

    it('should be available when only one of several selected assets can be spam', () => {
      set(collection, page([
        asset({ assetType: 'own chain', identifier: 'BTC' }),
        asset({ assetType: EVM_TOKEN, identifier: 'eip155:1/erc20:0xABC' }),
      ]));
      set(selected, ['BTC', 'eip155:1/erc20:0xABC']);

      const { spamDisabled } = table();

      expect(get(spamDisabled)).toBe(false);
    });

    it('should be unavailable when the selection names assets the page does not hold', () => {
      set(collection, page([asset({ assetType: EVM_TOKEN, identifier: 'eip155:1/erc20:0xABC' })]));
      set(selected, ['a-row-on-another-page']);

      const { spamDisabled } = table();

      expect(get(spamDisabled)).toBe(true);
    });
  });

  describe('which explorer can show an asset', () => {
    it('should send an evm token to its own chain', () => {
      const { getAssetLocation } = table();

      expect(getAssetLocation(asset({ assetType: EVM_TOKEN, evmChain: 'ethereum' }))).toBe('ethereum');
    });

    it('should send a solana token to solana', () => {
      const { getAssetLocation } = table();

      expect(getAssetLocation(asset({ assetType: SOLANA_TOKEN }))).toBe(SOLANA_CHAIN);
    });

    it('should offer no explorer for an evm token with no chain', () => {
      const { getAssetLocation } = table();

      expect(getAssetLocation(asset({ assetType: EVM_TOKEN, evmChain: null }))).toBeUndefined();
    });

    it('should offer no explorer for any other asset type', () => {
      const { getAssetLocation } = table();

      expect(getAssetLocation(asset({ assetType: 'own chain' }))).toBeUndefined();
    });
  });
});
