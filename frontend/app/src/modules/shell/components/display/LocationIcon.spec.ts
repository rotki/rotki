import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { PrivacyMode } from '@/modules/session/types';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

describe('locationIcon', () => {
  let wrapper: VueWrapper<InstanceType<typeof LocationIcon>>;
  let pinia: Pinia;

  function createWrapper(): VueWrapper<InstanceType<typeof LocationIcon>> {
    return mount(LocationIcon, {
      global: { plugins: [pinia] },
      props: { item: 'kraken' },
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

  it('should not blur the location by default', () => {
    expect(wrapper.find('.blur').exists()).toBe(false);
  });

  it('should blur the location in privacy mode', async () => {
    useFrontendSettingsStore().update({ privacyMode: PrivacyMode.SEMI_PRIVATE });
    await nextTick();
    expect(wrapper.find('.blur').exists()).toBe(true);
  });
});
