import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { PrivacyMode } from '@/modules/session/types';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import EvmChainIcon from '@/modules/shell/components/EvmChainIcon.vue';

describe('evmChainIcon', () => {
  let wrapper: VueWrapper<InstanceType<typeof EvmChainIcon>>;
  let pinia: Pinia;

  function createWrapper(): VueWrapper<InstanceType<typeof EvmChainIcon>> {
    return mount(EvmChainIcon, {
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
    useSettingsRepo().updateFrontend({ privacyMode: PrivacyMode.SEMI_PRIVATE });
    await nextTick();
    expect(wrapper.find('.blur').exists()).toBe(true);
  });
});
