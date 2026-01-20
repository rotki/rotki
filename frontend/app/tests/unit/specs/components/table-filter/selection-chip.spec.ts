import type { useAssetIconApi } from '@/composables/api/assets/icon';
import type { Suggestion } from '@/types/filtering';
import { createCustomPinia } from '@test/utils/create-pinia';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SelectionChip from '@/components/table-filter/SelectionChip.vue';

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    assetInfo: vi.fn().mockImplementation(identifier => ({
      identifier,
      evmChain: 'ethereum',
      symbol: 'ETH',
      isCustomAsset: false,
      name: 'Ethereum',
    })),
  }),
}));

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    checkAsset: vi.fn().mockResolvedValue(404),
    assetImageUrl: vi.fn(),
  } satisfies Partial<ReturnType<typeof useAssetIconApi>>),
}));

describe('table-filter/SelectionChip.vue', () => {
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
    it('renders a normal chip with RuiChip component', () => {
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

    it('emits click-item when chip is clicked', async () => {
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
      expect(wrapper.emitted('click-item')).toBeTruthy();
      expect(wrapper.emitted('click-item')?.[0]).toEqual([item]);
    });

    it('passes editMode to SuggestedItem', () => {
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

    it('passes suggestion to SuggestedItem', () => {
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
    it('renders a grouped chip with RuiMenu component', () => {
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

    it('displays the overflow count in the badge', () => {
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

    it('emits toggle-group-menu when overflow badge is clicked', async () => {
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

      expect(wrapper.emitted('toggle-group-menu')).toBeTruthy();
      expect(wrapper.emitted('toggle-group-menu')?.[0]).toEqual([item.key]);
    });

    it('emits remove-all-items when remove button is clicked', async () => {
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

      expect(wrapper.emitted('remove-all-items')).toBeTruthy();
      expect(wrapper.emitted('remove-all-items')?.[0]).toEqual([item.key]);
    });

    it('passes menu open state based on expandedGroupKey', () => {
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

    it('menu is closed when expandedGroupKey does not match', () => {
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

    it('menu is closed when expandedGroupKey is undefined', () => {
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
    it('renders a hidden div', () => {
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

    it('does not render any interactive content', () => {
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
    it('forwards cancel-edit event from SuggestedItem in normal mode', async () => {
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

      expect(wrapper.emitted('cancel-edit')).toBeTruthy();
      expect(wrapper.emitted('cancel-edit')?.[0]).toEqual([true]);
    });

    it('forwards update:search event from SuggestedItem in normal mode', async () => {
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

      expect(wrapper.emitted('update:search')).toBeTruthy();
      expect(wrapper.emitted('update:search')?.[0]).toEqual(['new-value']);
    });
  });
});
