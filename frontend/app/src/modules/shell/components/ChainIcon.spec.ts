import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { PrivacyMode } from '@/modules/session/types';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

describe('chainIcon', () => {
  let wrapper: VueWrapper<InstanceType<typeof ChainIcon>>;
  let pinia: Pinia;

  function createWrapper(): VueWrapper<InstanceType<typeof ChainIcon>> {
    return mount(ChainIcon, {
      global: { plugins: [pinia] },
      props: { chain: 'ethereum' },
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

  it('should not blur the chain icon by default', () => {
    expect(wrapper.find('.blur').exists()).toBe(false);
  });

  it('should blur the chain icon in privacy mode', async () => {
    useFrontendSettingsStore().update({ privacyMode: PrivacyMode.SEMI_PRIVATE });
    await nextTick();
    expect(wrapper.find('.blur').exists()).toBe(true);
  });
});
