import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import NewlyDetectedAssetToolbar from '@/modules/assets/detection/NewlyDetectedAssetToolbar.vue';
import { NewDetectedTokenKind } from '@/modules/assets/detection/types';

interface Props {
  allSelected?: boolean;
  selectedCount?: number;
  found?: number;
}

function mountToolbar(props: Props = {}): VueWrapper<InstanceType<typeof NewlyDetectedAssetToolbar>> {
  return mount(NewlyDetectedAssetToolbar, {
    props: {
      allSelected: false,
      found: 3,
      selectedCount: 1,
      tokenKindOptions: [{ title: 'EVM', value: NewDetectedTokenKind.EVM }],
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

  it('should disable the action buttons when nothing is selected', () => {
    const wrapper = mountToolbar({ selectedCount: 0 });
    expect(wrapper.find('[data-testid=accept-selected]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=mark-selected-spam]').attributes('disabled')).toBeDefined();
  });
});
