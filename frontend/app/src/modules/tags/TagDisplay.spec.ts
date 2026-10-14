import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import TagDisplay from '@/modules/tags/TagDisplay.vue';

describe('tagDisplay', () => {
  let wrapper: VueWrapper<InstanceType<typeof TagDisplay>>;
  let pinia: Pinia;

  function createWrapper(clickable: boolean): VueWrapper<InstanceType<typeof TagDisplay>> {
    return mount(TagDisplay, {
      global: { plugins: [pinia] },
      props: { clickable, tags: ['hardware'] },
    });
  }

  beforeEach((): void => {
    pinia = createPinia();
    setActivePinia(pinia);
    useSessionMetadataStore().allTags = {
      hardware: { backgroundColor: 'E3E3E3', description: 'a tag', foregroundColor: '000000', name: 'hardware' },
    };
  });

  afterEach((): void => {
    wrapper.unmount();
  });

  it('should leave the tags as plain labels by default', async () => {
    wrapper = createWrapper(false);
    const tag = wrapper.find('[data-testid=tag]');

    expect(tag.attributes('role')).toBeUndefined();
    await tag.trigger('click');
    expect(wrapper.emitted('select')).toBeUndefined();
  });

  it('should make each tag a button that emits it when clickable', async () => {
    wrapper = createWrapper(true);
    const tag = wrapper.find('[data-testid=tag]');

    expect(tag.attributes('role')).toBe('button');
    await tag.trigger('click');
    expect(wrapper.emitted('select')).toEqual([['hardware']]);
  });
});
