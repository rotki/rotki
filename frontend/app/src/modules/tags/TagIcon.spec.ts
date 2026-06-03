import type { Tag } from '@/modules/tags/tags';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { PrivacyMode } from '@/modules/session/types';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import TagIcon from '@/modules/tags/TagIcon.vue';

describe('tagIcon', () => {
  let wrapper: VueWrapper<InstanceType<typeof TagIcon>>;
  let pinia: Pinia;

  const tag: Tag = {
    backgroundColor: 'E3E3E3',
    description: 'a tag',
    foregroundColor: '000000',
    name: 'hardware',
  };

  function createWrapper(): VueWrapper<InstanceType<typeof TagIcon>> {
    return mount(TagIcon, {
      global: { plugins: [pinia] },
      props: { tag },
    });
  }

  beforeEach((): void => {
    pinia = createPinia();
    setActivePinia(pinia);
    wrapper = createWrapper();
  });

  afterEach((): void => {
    wrapper.unmount();
  });

  it('should not blur the tag by default', () => {
    expect(wrapper.find('.blur').exists()).toBe(false);
  });

  it('should blur the tag in privacy mode', async () => {
    useFrontendSettingsStore().update({ privacyMode: PrivacyMode.SEMI_PRIVATE });
    await nextTick();
    expect(wrapper.find('.blur').exists()).toBe(true);
  });
});
