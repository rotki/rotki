import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it } from 'vitest';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import AccountSettings from '@/pages/settings/account/index.vue';

describe('user-security-settings', () => {
  let wrapper: VueWrapper<InstanceType<typeof AccountSettings>>;

  function createWrapper(): VueWrapper<InstanceType<typeof AccountSettings>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(AccountSettings, {
      global: {
        plugins: [pinia],
        stubs: ['card-title', 'asset-select', 'asset-update', 'confirm-dialog', 'data-table', 'RouterLink'],
        provide: libraryDefaults,
      },
    });
  }

  beforeEach((): void => {
    wrapper = createWrapper();
  });

  it('should display no warning by default', () => {
    expect(wrapper.find('[data-cy=premium-warning]').exists()).toBe(false);
  });

  it('should display warning if premium sync enabled', async () => {
    const { premiumSync } = storeToRefs(usePremiumStore());
    set(premiumSync, true);
    await nextTick();
    expect(wrapper.find('[data-cy=premium-warning]').exists()).toBe(true);
  });
});
