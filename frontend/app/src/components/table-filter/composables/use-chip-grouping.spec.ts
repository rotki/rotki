import type { Suggestion } from '@/types/filtering';
import { get } from '@vueuse/shared';
import { describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useChipGrouping } from '@/components/table-filter/composables/use-chip-grouping';

describe('composables/use-chip-grouping', () => {
  function createSuggestion(key: string, value: string): Suggestion {
    return {
      asset: false,
      index: 0,
      key,
      total: 1,
      value,
    };
  }

  describe('groupedKeysCounts', () => {
    it('counts items per key correctly', () => {
      const selection = ref<Suggestion[]>([
        createSuggestion('type', 'value1'),
        createSuggestion('type', 'value2'),
        createSuggestion('status', 'active'),
      ]);
      const updateMatches = vi.fn();

      const { groupedKeysCounts } = useChipGrouping(selection, updateMatches);

      expect(get(groupedKeysCounts)).toEqual({
        status: 1,
        type: 2,
      });
    });

    it('returns empty object for empty selection', () => {
      const selection = ref<Suggestion[]>([]);
      const updateMatches = vi.fn();

      const { groupedKeysCounts } = useChipGrouping(selection, updateMatches);

      expect(get(groupedKeysCounts)).toEqual({});
    });
  });

  describe('groupedKeys', () => {
    it('identifies keys with more than 3 items', () => {
      const selection = ref<Suggestion[]>([
        createSuggestion('type', 'value1'),
        createSuggestion('type', 'value2'),
        createSuggestion('type', 'value3'),
        createSuggestion('type', 'value4'),
        createSuggestion('status', 'active'),
      ]);
      const updateMatches = vi.fn();

      const { groupedKeys } = useChipGrouping(selection, updateMatches);

      expect(get(groupedKeys).has('type')).toBe(true);
      expect(get(groupedKeys).has('status')).toBe(false);
    });

    it('does not group keys with exactly 3 items', () => {
      const selection = ref<Suggestion[]>([
        createSuggestion('type', 'value1'),
        createSuggestion('type', 'value2'),
        createSuggestion('type', 'value3'),
      ]);
      const updateMatches = vi.fn();

      const { groupedKeys } = useChipGrouping(selection, updateMatches);

      expect(get(groupedKeys).has('type')).toBe(false);
    });
  });

  describe('isKeyGrouped', () => {
    it('returns true for grouped keys', () => {
      const selection = ref<Suggestion[]>([
        createSuggestion('type', 'value1'),
        createSuggestion('type', 'value2'),
        createSuggestion('type', 'value3'),
        createSuggestion('type', 'value4'),
      ]);
      const updateMatches = vi.fn();

      const { isKeyGrouped } = useChipGrouping(selection, updateMatches);

      expect(isKeyGrouped('type')).toBe(true);
    });

    it('returns false for non-grouped keys', () => {
      const selection = ref<Suggestion[]>([
        createSuggestion('type', 'value1'),
        createSuggestion('type', 'value2'),
      ]);
      const updateMatches = vi.fn();

      const { isKeyGrouped } = useChipGrouping(selection, updateMatches);

      expect(isKeyGrouped('type')).toBe(false);
    });
  });

  describe('getChipDisplayType', () => {
    it('returns "normal" for non-grouped items', () => {
      const item = createSuggestion('type', 'value1');
      const selection = ref<Suggestion[]>([item]);
      const updateMatches = vi.fn();

      const { getChipDisplayType } = useChipGrouping(selection, updateMatches);

      expect(getChipDisplayType(item)).toBe('normal');
    });

    it('returns "grouped" for first item of grouped key', () => {
      const items = [
        createSuggestion('type', 'value1'),
        createSuggestion('type', 'value2'),
        createSuggestion('type', 'value3'),
        createSuggestion('type', 'value4'),
      ];
      const selection = ref<Suggestion[]>(items);
      const updateMatches = vi.fn();

      const { getChipDisplayType } = useChipGrouping(selection, updateMatches);

      expect(getChipDisplayType(get(selection)[0])).toBe('grouped');
    });

    it('returns "hidden" for non-first items of grouped key', () => {
      const items = [
        createSuggestion('type', 'value1'),
        createSuggestion('type', 'value2'),
        createSuggestion('type', 'value3'),
        createSuggestion('type', 'value4'),
      ];
      const selection = ref<Suggestion[]>(items);
      const updateMatches = vi.fn();

      const { getChipDisplayType } = useChipGrouping(selection, updateMatches);

      expect(getChipDisplayType(get(selection)[1])).toBe('hidden');
      expect(getChipDisplayType(get(selection)[2])).toBe('hidden');
      expect(getChipDisplayType(get(selection)[3])).toBe('hidden');
    });
  });

  describe('getGroupedOverflowCount', () => {
    it('returns count minus 1 for grouped keys', () => {
      const item = createSuggestion('type', 'value1');
      const selection = ref<Suggestion[]>([
        item,
        createSuggestion('type', 'value2'),
        createSuggestion('type', 'value3'),
        createSuggestion('type', 'value4'),
        createSuggestion('type', 'value5'),
      ]);
      const updateMatches = vi.fn();

      const { getGroupedOverflowCount } = useChipGrouping(selection, updateMatches);

      expect(getGroupedOverflowCount(item)).toBe(4);
    });

    it('returns -1 for non-existent keys', () => {
      const selection = ref<Suggestion[]>([]);
      const updateMatches = vi.fn();

      const { getGroupedOverflowCount } = useChipGrouping(selection, updateMatches);

      expect(getGroupedOverflowCount(createSuggestion('nonexistent', 'value'))).toBe(-1);
    });
  });

  describe('toggleGroupMenu', () => {
    it('sets expandedGroupKey when not expanded', () => {
      const selection = ref<Suggestion[]>([]);
      const updateMatches = vi.fn();

      const { expandedGroupKey, toggleGroupMenu } = useChipGrouping(selection, updateMatches);

      toggleGroupMenu('type');
      expect(get(expandedGroupKey)).toBe('type');
    });

    it('clears expandedGroupKey when already expanded', () => {
      const selection = ref<Suggestion[]>([]);
      const updateMatches = vi.fn();

      const { expandedGroupKey, toggleGroupMenu } = useChipGrouping(selection, updateMatches);

      toggleGroupMenu('type');
      toggleGroupMenu('type');
      expect(get(expandedGroupKey)).toBeUndefined();
    });

    it('switches to different key', () => {
      const selection = ref<Suggestion[]>([]);
      const updateMatches = vi.fn();

      const { expandedGroupKey, toggleGroupMenu } = useChipGrouping(selection, updateMatches);

      toggleGroupMenu('type');
      toggleGroupMenu('status');
      expect(get(expandedGroupKey)).toBe('status');
    });
  });

  describe('removeGroupedItem', () => {
    it('calls updateMatches with item removed', () => {
      const items = [
        createSuggestion('type', 'value1'),
        createSuggestion('type', 'value2'),
      ];
      const selection = ref<Suggestion[]>(items);
      const updateMatches = vi.fn();

      const { removeGroupedItem } = useChipGrouping(selection, updateMatches);

      removeGroupedItem(get(selection)[0]);
      expect(updateMatches).toHaveBeenCalledWith([get(selection)[1]]);
    });
  });

  describe('removeAllItemsForKey', () => {
    it('removes all items with the specified key', () => {
      const item1 = createSuggestion('type', 'value1');
      const item2 = createSuggestion('type', 'value2');
      const item3 = createSuggestion('status', 'active');
      const selection = ref<Suggestion[]>([item1, item2, item3]);
      const updateMatches = vi.fn();

      const { removeAllItemsForKey } = useChipGrouping(selection, updateMatches);

      removeAllItemsForKey('type');
      expect(updateMatches).toHaveBeenCalledWith([item3]);
    });

    it('clears expandedGroupKey after removal', () => {
      const selection = ref<Suggestion[]>([createSuggestion('type', 'value1')]);
      const updateMatches = vi.fn();

      const { expandedGroupKey, toggleGroupMenu, removeAllItemsForKey } = useChipGrouping(selection, updateMatches);

      toggleGroupMenu('type');
      removeAllItemsForKey('type');
      expect(get(expandedGroupKey)).toBeUndefined();
    });
  });

  describe('getGroupedItemsForKey', () => {
    it('returns all items for a specific key', () => {
      const item1 = createSuggestion('type', 'value1');
      const item2 = createSuggestion('type', 'value2');
      const item3 = createSuggestion('status', 'active');
      const selection = ref<Suggestion[]>([item1, item2, item3]);
      const updateMatches = vi.fn();

      const { getGroupedItemsForKey } = useChipGrouping(selection, updateMatches);

      expect(getGroupedItemsForKey(item1)).toEqual([item1, item2]);
    });

    it('returns empty array for non-existent key', () => {
      const selection = ref<Suggestion[]>([createSuggestion('type', 'value1')]);
      const updateMatches = vi.fn();

      const { getGroupedItemsForKey } = useChipGrouping(selection, updateMatches);

      expect(getGroupedItemsForKey(createSuggestion('nonexistent', 'value'))).toEqual([]);
    });
  });
});
