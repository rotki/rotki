import { type DOMWrapper, mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { getPublicPlaceholderImagePath } from '@/modules/core/common/file/file';
import AppImage from '@/modules/shell/components/AppImage.vue';

describe('appImage', () => {
  function createWrapper(props: InstanceType<typeof AppImage>['$props'] = {}): VueWrapper<InstanceType<typeof AppImage>> {
    return mount(AppImage, {
      global: { stubs: { RuiSkeletonLoader: true } },
      props,
    });
  }

  function image(wrapper: VueWrapper<InstanceType<typeof AppImage>>): DOMWrapper<Element> {
    return wrapper.find('img');
  }

  it('should apply no object-fit class when fit is not given', () => {
    const classes = image(createWrapper({ src: 'icon.svg' })).classes();

    expect(classes).not.toContain('object-contain');
    expect(classes).not.toContain('object-cover');
  });

  it('should apply object-contain when fit is contain', () => {
    const classes = image(createWrapper({ fit: 'contain', src: 'icon.svg' })).classes();

    expect(classes).toContain('object-contain');
    expect(classes).not.toContain('object-cover');
  });

  it('should apply object-cover when fit is cover', () => {
    const classes = image(createWrapper({ fit: 'cover', src: 'icon.svg' })).classes();

    expect(classes).toContain('object-cover');
    expect(classes).not.toContain('object-contain');
  });

  it('should keep imageClass alongside the object-fit class', () => {
    const classes = image(createWrapper({ fit: 'contain', imageClass: 'rounded-full', src: 'icon.svg' })).classes();

    expect(classes).toContain('object-contain');
    expect(classes).toContain('rounded-full');
  });

  it('should keep the object-fit class on the placeholder after an error', async () => {
    const wrapper = createWrapper({ fit: 'cover', src: 'missing.svg' });
    await image(wrapper).trigger('error');

    const fallback = image(wrapper);
    expect(fallback.attributes('src')).toBe(getPublicPlaceholderImagePath('image.svg'));
    expect(fallback.classes()).toContain('object-cover');
  });

  it('should render the skeleton instead of an image while loading', () => {
    const wrapper = createWrapper({ loading: true, src: 'icon.svg' });

    expect(wrapper.find('img').exists()).toBe(false);
    expect(wrapper.findComponent({ name: 'RuiSkeletonLoader' }).exists()).toBe(true);
  });
});
