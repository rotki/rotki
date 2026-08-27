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

const modelSearch = ref<string>('');
const visibleAssets = ref<AssetInfoWithId[]>([]);
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

  it('should not prefill the search box with the seed, which the user would have to clear before typing', () => {
    createWrapper([]);
    expect(get(modelSearch)).toBe('');
  });

  it('should seed on the selected asset symbol rather than ETH, so its siblings on other chains are listed', () => {
    createWrapper([USDC]);
    expect(preload).toHaveBeenCalledWith('USDC');
    expect(get(modelSearch)).toBe('');
  });

  it('should not seed a list the search already returned', () => {
    set(visibleAssets, [asset(DAI, 'DAI')]);
    createWrapper([]);
    expect(preload).not.toHaveBeenCalled();
  });

  it('should pin the selected asset above the search results, and declare it pinned so the highlight skips it', () => {
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
