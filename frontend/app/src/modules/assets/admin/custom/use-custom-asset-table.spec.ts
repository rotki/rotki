import type { CustomAsset } from '@/modules/assets/types';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { effectScope, type Ref, ref } from 'vue';
import { useCustomAssetTable } from './use-custom-asset-table';

function asset(overrides: Partial<CustomAsset> = {}): CustomAsset {
  return { customAssetType: 'real estate', identifier: 'custom-1', name: 'A house', notes: '', ...overrides };
}

let expanded: Ref<CustomAsset[]>;
let scope: ReturnType<typeof effectScope>;

function table(): ReturnType<typeof useCustomAssetTable> {
  scope = effectScope();
  return scope.run(() => useCustomAssetTable(expanded))!;
}

describe('modules/assets/admin/custom/useCustomAssetTable', () => {
  beforeEach(() => {
    expanded = ref<CustomAsset[]>([]);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the columns', () => {
    it('should offer asset, type and actions', () => {
      const { cols } = table();

      expect(get(cols).map(col => col.key)).toEqual(['name', 'custom_asset_type', 'actions']);
    });

    it('should let the user sort by asset and type, but not by actions', () => {
      const { cols } = table();

      expect(get(cols).map(col => !!col.sortable)).toEqual([true, true, false]);
    });
  });

  describe('shaping a row for the shared asset display', () => {
    it('should mark it as a custom asset and show its type as the symbol', () => {
      const { getAsset } = table();

      expect(getAsset(asset())).toEqual({
        customAssetType: 'real estate',
        identifier: 'custom-1',
        isCustomAsset: true,
        name: 'A house',
        symbol: 'real estate',
      });
    });
  });

  describe('expanding a row', () => {
    it('should report nothing expanded to begin with', () => {
      const { isExpanded } = table();

      expect(isExpanded('custom-1')).toBe(false);
    });

    it('should expand the row it is given', () => {
      const { expand, isExpanded } = table();
      expand(asset());

      expect(isExpanded('custom-1')).toBe(true);
    });

    it('should collapse a row that is already expanded', () => {
      const { expand, isExpanded } = table();
      expand(asset());
      expand(asset());

      expect(isExpanded('custom-1')).toBe(false);
      expect(get(expanded)).toEqual([]);
    });

    it('should keep only one row open at a time', () => {
      const { expand, isExpanded } = table();
      expand(asset({ identifier: 'custom-1' }));
      expand(asset({ identifier: 'custom-2' }));

      expect(isExpanded('custom-1')).toBe(false);
      expect(isExpanded('custom-2')).toBe(true);
      expect(get(expanded)).toHaveLength(1);
    });

    it('should report only the identifier it was asked about', () => {
      const { expand, isExpanded } = table();
      expand(asset({ identifier: 'custom-1' }));

      expect(isExpanded('custom-2')).toBe(false);
    });
  });
});
