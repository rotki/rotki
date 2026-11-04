import type { LocationIcon } from '@/modules/locations/location-icons';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import LocationIconPicker from '@/modules/locations/components/LocationIconPicker.vue';
import '@test/i18n';

const mapPin: LocationIcon = 'lu-map-pin';

describe('locationIconPicker', () => {
  it('should name every icon button for screen readers and tooltips', () => {
    const wrapper = mount(LocationIconPicker, { props: { modelValue: mapPin } });
    const piggyBank = wrapper.find('[data-testid=location-icon-lu-piggy-bank]');
    expect(piggyBank.attributes('aria-label')).toBe('location_manager.form.icon_option::piggy bank');
    expect(piggyBank.attributes('title')).toBe('location_manager.form.icon_option::piggy bank');
  });

  it('should pick the clicked icon and mark it pressed', async () => {
    const wrapper = mount(LocationIconPicker, {
      props: {
        'modelValue': mapPin,
        'onUpdate:modelValue': async (value: LocationIcon) => wrapper.setProps({ modelValue: value }),
      },
    });
    await wrapper.find('[data-testid=location-icon-lu-vault]').trigger('click');
    expect(wrapper.emitted('update:modelValue')).toEqual([['lu-vault']]);
    expect(wrapper.find('[data-testid=location-icon-lu-vault]').attributes('aria-pressed')).toBe('true');
  });
});
