import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it } from 'vitest';
import UnmatchedCardList from '@/modules/history/events/UnmatchedCardList.vue';

interface TestItem {
  id: string;
  label: string;
}

function createItems(count: number): TestItem[] {
  return Array.from({ length: count }, (_item, index) => ({
    id: `item-${index}`,
    label: `Item ${index}`,
  }));
}

const selected = ref<string[]>([]);

/**
 * Mounted through a host component: the list is generic, so this is what pins the
 * item type and lets the selection model be asserted the way a caller sees it.
 */
function mountList(items: TestItem[], highlightedId?: string): VueWrapper {
  return mount({
    components: { UnmatchedCardList },
    setup() {
      return {
        highlighted: (item: TestItem): boolean => item.id === highlightedId,
        items,
        rowKey: (item: TestItem): string => item.id,
        selected,
      };
    },
    template: `
      <UnmatchedCardList
        v-model:selected="selected"
        :items="items"
        :row-key="rowKey"
        :highlighted="highlighted"
        empty-description="Nothing here"
        max-height="20rem"
      >
        <template #header="{ item }">
          <span>{{ item.label }}</span>
        </template>
      </UnmatchedCardList>
    `,
  }, {
    global: { provide: libraryDefaults },
  });
}

describe('modules/history/events/UnmatchedCardList', () => {
  beforeEach(() => {
    set(selected, []);
  });

  it('should render a card per item', () => {
    const wrapper = mountList(createItems(3));

    expect(wrapper.findAll('[data-testid=unmatched-card]')).toHaveLength(3);
    expect(wrapper.text()).toContain('Item 0');
    expect(wrapper.find('[data-testid=unmatched-card-empty]').exists()).toBe(false);
  });

  it('should show the empty description when there is nothing to act on', () => {
    const wrapper = mountList([]);

    expect(wrapper.find('[data-testid=unmatched-card-empty]').text()).toContain('Nothing here');
    expect(wrapper.find('[data-testid=unmatched-card-select-all]').exists()).toBe(false);
  });

  it('should page like the table instead of rendering everything', async () => {
    const wrapper = mountList(createItems(23));

    expect(wrapper.findAll('[data-testid=unmatched-card]')).toHaveLength(10);
    expect(wrapper.find('[data-testid=unmatched-card-pagination]').exists()).toBe(true);

    await wrapper.findComponent({ name: 'RuiTablePagination' }).vm.$emit('update:modelValue', {
      limit: 10,
      limits: [10, 25, 50],
      page: 3,
      total: 23,
    });

    expect(wrapper.findAll('[data-testid=unmatched-card]')).toHaveLength(3);
    expect(wrapper.text()).toContain('Item 22');
  });

  it('should hide the pager while everything fits on one page', () => {
    const wrapper = mountList(createItems(10));

    expect(wrapper.find('[data-testid=unmatched-card-pagination]').exists()).toBe(false);
  });

  it('should select every item, not only the visible page', async () => {
    const wrapper = mountList(createItems(12));

    await wrapper.findComponent({ name: 'RuiCheckbox' }).vm.$emit('update:modelValue', true);

    expect(get(selected)).toHaveLength(12);
  });

  it('should select everything on the first click even when the checkbox reports otherwise', async () => {
    // RuiCheckbox's native input starts out `checked`, so the first click emits `false` over
    // an empty selection. Acting on that payload made select-all a no-op until clicked twice.
    const wrapper = mountList(createItems(12));

    await wrapper.findComponent({ name: 'RuiCheckbox' }).vm.$emit('update:modelValue', false);

    expect(get(selected)).toHaveLength(12);
  });

  it('should clear the selection when everything is already selected', async () => {
    set(selected, createItems(12).map(item => item.id));
    const wrapper = mountList(createItems(12));

    await wrapper.findComponent({ name: 'RuiCheckbox' }).vm.$emit('update:modelValue', true);

    expect(get(selected)).toHaveLength(0);
  });

  it('should leave selections from other lists alone when clearing', async () => {
    set(selected, ['item-0', 'item-1', 'foreign-key']);
    const wrapper = mountList(createItems(2));

    await wrapper.findComponent({ name: 'RuiCheckbox' }).vm.$emit('update:modelValue', true);

    expect(get(selected)).toEqual(['foreign-key']);
  });

  it('should toggle a single card without touching the rest', async () => {
    set(selected, ['item-0']);
    const wrapper = mountList(createItems(3));
    const checkboxes = wrapper.findAllComponents({ name: 'RuiCheckbox' });

    // index 0 is select-all, so the second checkbox is the first card
    await checkboxes[2].vm.$emit('update:modelValue', true);

    expect(get(selected)).toEqual(['item-0', 'item-1']);
  });

  it('should highlight the card a deep link points at', () => {
    const wrapper = mountList(createItems(3), 'item-1');

    expect(wrapper.find('[data-testid=unmatched-card][data-key="item-1"]').classes()).toContain('!bg-rui-warning/15');
    expect(wrapper.find('[data-testid=unmatched-card][data-key="item-0"]').classes()).not.toContain('!bg-rui-warning/15');
  });
});
