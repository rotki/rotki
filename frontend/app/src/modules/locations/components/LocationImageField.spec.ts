import type { LocationIcon } from '@/modules/locations/location-icons';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import LocationImageField from '@/modules/locations/components/LocationImageField.vue';
import '@test/i18n';

type Pending = File | null | undefined;

const landmark: LocationIcon = 'lu-landmark';

const RuiFileUpload = {
  emits: ['update:modelValue'],
  props: ['modelValue', 'accept'],
  template: '<div data-testid="location-image-upload" :data-accept="accept" :data-file="modelValue?.name" />',
};

function createWrapper(props: { pending: Pending; image: string | null; identifier?: string }): VueWrapper<InstanceType<typeof LocationImageField>> {
  const wrapper = mount(LocationImageField, {
    global: {
      stubs: {
        AppImage: { props: ['src'], template: '<img :src="src" data-testid="location-image-preview" />' },
        RuiFileUpload,
      },
    },
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

describe('locationImageField', () => {
  it('should hold a file chosen in the dropzone for the form instead of uploading it', async () => {
    const wrapper = createWrapper({ image: null, pending: undefined });
    const file = new File(['png'], 'logo.png', { type: 'image/png' });
    await wrapper.findComponent(RuiFileUpload).vm.$emit('update:modelValue', file);
    expect(wrapper.emitted('update:modelValue')).toEqual([[file]]);
    expect(wrapper.find('[data-testid=location-image-preview]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=location-image-upload]').attributes('data-file')).toBe('logo.png');
  });

  it('should keep the stored image when a chosen file is cleared', async () => {
    const wrapper = createWrapper({ identifier: 'custom:ing', image: 'ing.png', pending: new File(['png'], 'logo.png') });
    await wrapper.findComponent(RuiFileUpload).vm.$emit('update:modelValue', undefined);
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
    expect(wrapper.find('[data-testid=location-image-preview]').attributes('src')).toContain('ing.png');
  });

  it('should mark a stored image for removal', async () => {
    const wrapper = createWrapper({ identifier: 'custom:ing', image: 'ing.png', pending: undefined });
    expect(wrapper.find('[data-testid=location-image-preview]').attributes('src')).toContain('ing.png');
    await wrapper.find('[data-testid=location-image-remove]').trigger('click');
    expect(wrapper.emitted('update:modelValue')).toEqual([[null]]);
    expect(wrapper.find('[data-testid=location-image-preview]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=location-image-remove]').exists()).toBe(false);
  });

  it('should still remove the stored image when a file chosen after removing it is cleared', async () => {
    const wrapper = createWrapper({ identifier: 'custom:ing', image: 'ing.png', pending: undefined });
    await wrapper.find('[data-testid=location-image-remove]').trigger('click');
    const file = new File(['png'], 'logo.png');
    await wrapper.findComponent(RuiFileUpload).vm.$emit('update:modelValue', file);

    await wrapper.findComponent(RuiFileUpload).vm.$emit('update:modelValue', undefined);

    expect(wrapper.emitted('update:modelValue')).toEqual([[null], [file], [null]]);
    expect(wrapper.find('[data-testid=location-image-preview]').exists()).toBe(false);
  });

  it('should keep the stored image after the form drops a pending removal', async () => {
    const wrapper = createWrapper({ identifier: 'custom:ing', image: 'ing.png', pending: undefined });
    await wrapper.find('[data-testid=location-image-remove]').trigger('click');
    await wrapper.setProps({ modelValue: undefined });
    await wrapper.findComponent(RuiFileUpload).vm.$emit('update:modelValue', new File(['png'], 'logo.png'));

    await wrapper.findComponent(RuiFileUpload).vm.$emit('update:modelValue', undefined);

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([undefined]);
  });

  it('should offer no removal while nothing is stored', () => {
    const wrapper = createWrapper({ image: null, pending: new File(['png'], 'logo.png') });
    expect(wrapper.find('[data-testid=location-image-remove]').exists()).toBe(false);
  });
});
