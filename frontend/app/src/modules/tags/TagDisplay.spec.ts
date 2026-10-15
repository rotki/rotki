import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import TagDisplay from '@/modules/tags/TagDisplay.vue';

describe('tagDisplay', () => {
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

  it('should leave the tags as plain labels by default', async () => {
    const wrapper = createWrapper(false);
    const tag = wrapper.find('[data-testid=tag]');

    expect(tag.attributes('title')).toBeUndefined();
    await tag.trigger('click');
    expect(wrapper.emitted('select')).toBeUndefined();
  });

  it('should offer each tag as a filter and emit it when clickable', async () => {
    const wrapper = createWrapper(true);
    const tag = wrapper.find('[data-testid=tag]');

    expect(tag.attributes('title')).toBe('tag_display.filter_by::hardware');
    await tag.trigger('click');
    expect(wrapper.emitted('select')).toEqual([['hardware']]);
  });
});
