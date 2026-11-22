import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import MissingMappingDismissButton from '@/modules/assets/admin/missing-mappings/MissingMappingDismissButton.vue';

describe('missingMappingDismissButton', () => {
  it('should emit dismiss when clicked', async () => {
    const wrapper = mount(MissingMappingDismissButton, {
      global: { stubs: { RuiTooltip: { template: '<div><slot name="activator" /><slot /></div>' } } },
    });

    await wrapper.find('[data-testid="row-dismiss"]').trigger('click');

    expect(wrapper.emitted('dismiss')).toEqual([[]]);
  });

  it('should say the row comes back if the exchange reports the asset again', () => {
    const wrapper = mount(MissingMappingDismissButton, {
      global: { stubs: { RuiTooltip: { template: '<div><slot name="activator" /><slot /></div>' } } },
    });

    expect(wrapper.text()).toContain('asset_management.cex_mapping.dismiss_hint');
  });
});
