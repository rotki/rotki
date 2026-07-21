import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import NewlyDetectedAssetRowActions from '@/modules/assets/detection/NewlyDetectedAssetRowActions.vue';

function mountRowActions(): VueWrapper<InstanceType<typeof NewlyDetectedAssetRowActions>> {
  return mount(NewlyDetectedAssetRowActions);
}

describe('modules/assets/detection/NewlyDetectedAssetRowActions', () => {
  it('should emit accept when the accept button is clicked', async () => {
    const wrapper = mountRowActions();
    await wrapper.find('[data-testid=accept-token]').trigger('click');
    expect(wrapper.emitted('accept')).toHaveLength(1);
  });

  it('should emit mark-spam when the spam button is clicked', async () => {
    const wrapper = mountRowActions();
    await wrapper.find('[data-testid=mark-token-spam]').trigger('click');
    expect(wrapper.emitted('mark-spam')).toHaveLength(1);
  });
});
