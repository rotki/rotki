import type { LocationIcon } from '@/modules/locations/location-icons';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import LocationImageField from '@/modules/locations/components/LocationImageField.vue';
import '@test/i18n';

type Pending = File | null | undefined;

const landmark: LocationIcon = 'lu-landmark';

function createWrapper(props: { pending: Pending; image: string | null; identifier?: string }): VueWrapper<InstanceType<typeof LocationImageField>> {
  const wrapper = mount(LocationImageField, {
    global: { stubs: { AppImage: { props: ['src'], template: '<img :src="src" data-testid="location-image-preview" />' } } },
    props: {
      'icon': landmark,
      'identifier': props.identifier,
      'image': props.image,
      'modelValue': props.pending,
      'onUpdate:modelValue': async (value: Pending) => wrapper.setProps({ modelValue: value }),
    },
  });
  return wrapper;
}

async function choose(wrapper: VueWrapper, file: File): Promise<void> {
  const input = wrapper.find('[data-testid=location-image-input]');
  Object.defineProperty(input.element, 'files', { configurable: true, value: [file] });
  await input.trigger('change');
}

describe('locationImageField', () => {
  it('should hold a chosen file for the form instead of uploading it', async () => {
    const wrapper = createWrapper({ image: null, pending: undefined });
    const file = new File(['png'], 'logo.png', { type: 'image/png' });
    await choose(wrapper, file);
    expect(wrapper.emitted('update:modelValue')).toEqual([[file]]);
    expect(wrapper.find('[data-testid=location-image-remove]').exists()).toBe(true);
  });

  it('should mark a stored image for removal', async () => {
    const wrapper = createWrapper({ identifier: 'custom:ing', image: 'ing.png', pending: undefined });
    expect(wrapper.find('[data-testid=location-image-preview]').attributes('src')).toContain('ing.png');
    await wrapper.find('[data-testid=location-image-remove]').trigger('click');
    expect(wrapper.emitted('update:modelValue')).toEqual([[null]]);
    expect(wrapper.find('[data-testid=location-image-preview]').exists()).toBe(false);
  });

  it('should drop a chosen file without asking to remove anything when none is stored', async () => {
    const wrapper = createWrapper({ image: null, pending: new File(['png'], 'logo.png') });
    await wrapper.find('[data-testid=location-image-remove]').trigger('click');
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });
});
