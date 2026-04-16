import type { useAssetIconApi } from '@/modules/assets/api/use-asset-icon-api';
import type { Suggestion } from '@/modules/core/table/filtering';
import { createCustomPinia } from '@test/utils/create-pinia';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SelectionChip from '@/modules/core/table/SelectionChip.vue';

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    getAssetInfo: vi.fn().mockImplementation((identifier: string | undefined) => ({
      identifier,
      evmChain: 'ethereum',
      symbol: 'ETH',
      isCustomAsset: false,
      name: 'Ethereum',
    })),
  }),
}));

vi.mock('@/modules/assets/api/use-asset-icon-api', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    checkAsset: vi.fn().mockResolvedValue(404),
    assetImageUrl: vi.fn(),
  } satisfies Partial<ReturnType<typeof useAssetIconApi>>),
}));

describe('selection-chip', () => {
  let wrapper: VueWrapper<InstanceType<typeof SelectionChip>>;

  function createSuggestion(key: string, value: string, exclude = false): Suggestion {
    return {
      asset: false,
      exclude,
      index: 0,
      key,
      total: 1,
      value,
    };
  }

  function createWrapper(options: ComponentMountingOptions<typeof SelectionChip> = {}): VueWrapper<InstanceType<typeof SelectionChip>> {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    return mount(SelectionChip, {
      global: {
        plugins: [pinia],
      },
      ...options,
    });
  }

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  describe('displayType="normal"', () => {
    it('should render a normal chip with RuiChip component', () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'normal',
          editMode: false,
          overflowCount: 0,
          groupedItems: [],
        },
      });

      const chip = wrapper.findComponent({ name: 'RuiChip' });
      expect(chip.exists()).toBe(true);
      expect(wrapper.findComponent({ name: 'RuiMenu' }).exists()).toBe(false);
      expect(wrapper.find('[data-testid=hidden-selection-chip]').exists()).toBe(false);
    });

    it('should emit click-item when chip is clicked', async () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'normal',
          editMode: false,
          overflowCount: 0,
          groupedItems: [],
        },
      });

      const chip = wrapper.findComponent({ name: 'RuiChip' });
      await chip.trigger('click');
      expect(wrapper.emitted('click-item')).toBeDefined();
      expect(wrapper.emitted('click-item')?.[0]).toEqual([item]);
    });

    it('should pass editMode to SuggestedItem', () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'normal',
          editMode: true,
          overflowCount: 0,
          groupedItems: [],
        },
      });

      const suggestedItem = wrapper.findComponent({ name: 'SuggestedItem' });
      expect(suggestedItem.props('editMode')).toBe(true);
    });

    it('should pass suggestion to SuggestedItem', () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'normal',
          editMode: false,
          overflowCount: 0,
          groupedItems: [],
        },
      });

      const suggestedItem = wrapper.findComponent({ name: 'SuggestedItem' });
      expect(suggestedItem.props('suggestion')).toStrictEqual(item);
    });
  });

  describe('displayType="grouped"', () => {
    it('should render a grouped chip with RuiMenu component', () => {
      const item = createSuggestion('type', 'value1');
      const groupedItems = [
        createSuggestion('type', 'value1'),
        createSuggestion('type', 'value2'),
        createSuggestion('type', 'value3'),
        createSuggestion('type', 'value4'),
      ];

      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'grouped',
          editMode: false,
          overflowCount: 3,
          groupedItems,
        },
      });

      expect(wrapper.findComponent({ name: 'RuiMenu' }).exists()).toBe(true);
    });

    it('should display the overflow count in the badge', () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'grouped',
          editMode: false,
          overflowCount: 5,
          groupedItems: [],
        },
      });

      expect(wrapper.text()).toContain('5+');
    });

    it('should emit toggle-group-menu when overflow badge is clicked', async () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'grouped',
          editMode: false,
          overflowCount: 3,
          groupedItems: [],
        },
      });

      const overflowBadge = wrapper.find('.bg-rui-primary');
      await overflowBadge.trigger('click');

      expect(wrapper.emitted('toggle-group-menu')).toBeDefined();
      expect(wrapper.emitted('toggle-group-menu')?.[0]).toEqual([item.key]);
    });

    it('should emit remove-all-items when remove button is clicked', async () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'grouped',
          editMode: false,
          overflowCount: 3,
          groupedItems: [],
        },
      });

      const removeButton = wrapper.findComponent({ name: 'RuiButton' });
      await removeButton.trigger('click');

      expect(wrapper.emitted('remove-all-items')).toBeDefined();
      expect(wrapper.emitted('remove-all-items')?.[0]).toEqual([item.key]);
    });

    it('should pass menu open state based on expandedGroupKey', () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'grouped',
          editMode: false,
          expandedGroupKey: 'type',
          overflowCount: 3,
          groupedItems: [],
        },
      });

      const menu = wrapper.findComponent({ name: 'RuiMenu' });
      expect(menu.props('modelValue')).toBe(true);
    });

    it('should close menu when expandedGroupKey does not match', () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'grouped',
          editMode: false,
          expandedGroupKey: 'other',
          overflowCount: 3,
          groupedItems: [],
        },
      });

      const menu = wrapper.findComponent({ name: 'RuiMenu' });
      expect(menu.props('modelValue')).toBe(false);
    });

    it('should close menu when expandedGroupKey is undefined', () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'grouped',
          editMode: false,
          overflowCount: 3,
          groupedItems: [],
        },
      });

      const menu = wrapper.findComponent({ name: 'RuiMenu' });
      expect(menu.props('modelValue')).toBe(false);
    });
  });

  describe('displayType="hidden"', () => {
    it('should render a hidden div', () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'hidden',
          editMode: false,
          overflowCount: 0,
          groupedItems: [],
        },
      });

      expect(wrapper.find('[data-testid=hidden-selection-chip]').exists()).toBe(true);
      expect(wrapper.findComponent({ name: 'RuiChip' }).exists()).toBe(false);
      expect(wrapper.findComponent({ name: 'RuiMenu' }).exists()).toBe(false);
    });

    it('should not render any interactive content', () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'hidden',
          editMode: false,
          overflowCount: 0,
          groupedItems: [],
        },
      });

      expect(wrapper.findComponent({ name: 'SuggestedItem' }).exists()).toBe(false);
    });
  });

  describe('event forwarding', () => {
    it('should forward cancel-edit event from SuggestedItem in normal mode', async () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'normal',
          editMode: true,
          overflowCount: 0,
          groupedItems: [],
        },
      });

      const suggestedItem = wrapper.findComponent({ name: 'SuggestedItem' });
      await suggestedItem.vm.$emit('cancel-edit', true);

      expect(wrapper.emitted('cancel-edit')).toBeDefined();
      expect(wrapper.emitted('cancel-edit')?.[0]).toEqual([true]);
    });

    it('should forward update:search event from SuggestedItem in normal mode', async () => {
      const item = createSuggestion('type', 'value1');
      wrapper = createWrapper({
        props: {
          item,
          chipAttrs: {},
          displayType: 'normal',
          editMode: true,
          overflowCount: 0,
          groupedItems: [],
        },
      });

      const suggestedItem = wrapper.findComponent({ name: 'SuggestedItem' });
      await suggestedItem.vm.$emit('update:search', 'new-value');

      expect(wrapper.emitted('update:search')).toBeDefined();
      expect(wrapper.emitted('update:search')?.[0]).toEqual(['new-value']);
    });
  });
});
