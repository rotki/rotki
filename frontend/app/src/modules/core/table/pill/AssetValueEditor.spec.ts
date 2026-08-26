import type { AssetInfoWithId } from '@rotki/common';
import type { ActiveFilter, FieldDef } from '@/modules/core/table/pill/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetValueEditor from '@/modules/core/table/pill/AssetValueEditor.vue';
import ValueSelectList from '@/modules/core/table/pill/ValueSelectList.vue';

const USDC = 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
const DAI = 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F';

function asset(identifier: string, symbol: string): AssetInfoWithId {
  return { identifier, isCustomAsset: false, name: `${symbol} coin`, symbol };
}

// The search is driven entirely by `useAssetSearch`; the editor only decides what to seed it with
// and how to order what comes back. Both are observable through these handles.
const modelSearch = ref<string>('');
const visibleAssets = ref<AssetInfoWithId[]>([]);
// Resolves rather than returning undefined: the editor hands the result to `startPromise`.
const preload = vi.fn<(keyword: string) => Promise<void>>(async () => {});

vi.mock('@/modules/shell/components/inputs/use-asset-search', () => ({
  useAssetSearch: (): Record<string, unknown> => ({
    error: ref(''),
    getVisibleAsset: (identifier: string): AssetInfoWithId | undefined =>
      get(visibleAssets).find(item => item.identifier === identifier),
    loading: ref(false),
    modelSearch,
    preload,
    visibleAssets,
  }),
}));

const field: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'filter' },
  display: 'asset',
  key: 'assets',
  label: 'Asset',
  multiple: false,
  operators: ['is'],
  resolveLabel: (value: string): string => (value === USDC ? 'USDC' : 'DAI'),
  valueType: 'asset',
};

function createWrapper(values: string[]): VueWrapper {
  const filter: ActiveFilter = { fieldKey: 'assets', op: 'is', values };
  return mount(AssetValueEditor, {
    global: { stubs: { AssetIcon: true, RuiButton: true, RuiButtonGroup: true, ValueSelectList: true } },
    props: { field, filter },
  });
}

function listProps(wrapper: VueWrapper): Record<string, any> {
  return wrapper.findComponent(ValueSelectList).props();
}

describe('assetValueEditor', () => {
  beforeEach(() => {
    set(modelSearch, '');
    set(visibleAssets, []);
    preload.mockClear();
  });

  it('should seed a common asset when nothing is selected yet', () => {
    createWrapper([]);
    expect(preload).toHaveBeenCalledWith('ETH');
  });

  // The seed only exists so the list is not empty on open. Putting it through `modelSearch` would
  // show `ETH` in the search box as text the user has to clear before typing their own.
  it('should not prefill the search box with the seed', () => {
    createWrapper([]);
    expect(get(modelSearch)).toBe('');
  });

  // Reopening a pill is usually about swapping the asset for a sibling — the same symbol on
  // another chain — so the list opens on the selection's own symbol rather than on `ETH` or on a
  // single row. Still without prefilling the box.
  it('should seed on the selected asset symbol when there is one', () => {
    createWrapper([USDC]);
    expect(preload).toHaveBeenCalledWith('USDC');
    expect(get(modelSearch)).toBe('');
  });

  it('should not seed a list the search already returned', () => {
    set(visibleAssets, [asset(DAI, 'DAI')]);
    createWrapper([]);
    expect(preload).not.toHaveBeenCalled();
  });

  // A single-select list has no chip row, so the asset being filtered on has to hold a place in
  // the options themselves or it scrolls out of sight as soon as the user searches for anything
  // else. It is pinned first, and declared as pinned so the highlight skips past it.
  it('should pin the selected asset above the search results', () => {
    set(visibleAssets, [asset(DAI, 'DAI'), asset(USDC, 'USDC')]);
    const props = listProps(createWrapper([USDC]));
    expect(props.options.map((option: { value: string }) => option.value)).toStrictEqual([USDC, DAI]);
    expect(props.pinned).toBe(1);
  });

  it('should drop an asset that was selected and then deselected', async () => {
    set(visibleAssets, [asset(USDC, 'USDC')]);
    const wrapper = createWrapper([USDC]);

    wrapper.findComponent(ValueSelectList).vm.$emit('update:modelValue', [USDC]);
    await nextTick();

    set(visibleAssets, [asset(DAI, 'DAI')]);
    await wrapper.setProps({ field, filter: { fieldKey: 'assets', op: 'is', values: [DAI] } });

    expect(listProps(wrapper).options.map((option: { value: string }) => option.value)).toStrictEqual([DAI]);
  });

  it('should pin nothing when no asset is selected', () => {
    set(visibleAssets, [asset(DAI, 'DAI'), asset(USDC, 'USDC')]);
    const props = listProps(createWrapper([]));
    expect(props.options.map((option: { value: string }) => option.value)).toStrictEqual([DAI, USDC]);
    expect(props.pinned).toBe(0);
  });
});
