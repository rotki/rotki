import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import NewlyDetectedAssetToolbar from '@/modules/assets/detection/NewlyDetectedAssetToolbar.vue';

interface Props {
  allSelected?: boolean;
  selectedCount?: number;
  found?: number;
  fields?: FieldDef[];
}

function mountToolbar(props: Props = {}): VueWrapper<InstanceType<typeof NewlyDetectedAssetToolbar>> {
  return mount(NewlyDetectedAssetToolbar, {
    props: {
      allSelected: false,
      fields: [],
      filters: {},
      found: 3,
      selectedCount: 1,
      ...props,
    },
  });
}

describe('modules/assets/detection/NewlyDetectedAssetToolbar', () => {
  it('should emit accept when the accept-selected button is clicked', async () => {
    const wrapper = mountToolbar({ selectedCount: 2 });
    await wrapper.find('[data-testid=accept-selected]').trigger('click');
    expect(wrapper.emitted('accept')).toHaveLength(1);
  });

  it('should emit mark-spam when the mark-selected-spam button is clicked', async () => {
    const wrapper = mountToolbar({ selectedCount: 2 });
    await wrapper.find('[data-testid=mark-selected-spam]').trigger('click');
    expect(wrapper.emitted('mark-spam')).toHaveLength(1);
  });

  it('should show no selection actions, only the hint and the filter, when nothing is selected', () => {
    const wrapper = mountToolbar({ selectedCount: 0 });
    expect(wrapper.find('[data-testid=table-selection-bar]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=accept-selected]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=mark-selected-spam]').exists()).toBe(false);
  });

  it('should offer to widen the selection to every matching token until all are selected', async () => {
    const partial = mountToolbar({ found: 5, selectedCount: 2 });
    await partial.find('[data-testid=select-all-matching]').trigger('click');
    expect(partial.emitted('toggle-selection')).toHaveLength(1);

    const all = mountToolbar({ allSelected: true, found: 5, selectedCount: 5 });
    expect(all.find('[data-testid=select-all-matching]').exists()).toBe(false);
  });

  it('should ask to clear the selection from the bar', async () => {
    const wrapper = mountToolbar({ selectedCount: 2 });
    await wrapper.find('[data-testid=table-selection-clear]').trigger('click');
    expect(wrapper.emitted('clear-selection')).toHaveLength(1);
  });
});
