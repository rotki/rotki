import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AccountSettings from '@/pages/settings/account/index.vue';
import { usePremiumStore } from '@/store/session/premium';
import { libraryDefaults } from '../../../utils/provide-defaults';

vi.mock('vue-router', () => ({
  useRoute: vi.fn().mockImplementation(() => ref({})),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(),
  }),
  createRouter: vi.fn().mockImplementation(() => ({
    beforeEach: vi.fn(),
  })),
  createWebHashHistory: vi.fn(),
}));

describe('userSecuritySettings.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof AccountSettings>>;

  function createWrapper() {
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

  beforeEach(() => {
    wrapper = createWrapper();
  });

  it('displays no warning by default', () => {
    expect(wrapper.find('[data-cy=premium-warning]').exists()).toBe(false);
  });

  it('displays warning if premium sync enabled', async () => {
    const { premiumSync } = storeToRefs(usePremiumStore());
    set(premiumSync, true);
    await nextTick();
    expect(wrapper.find('[data-cy=premium-warning]').exists()).toBe(true);
  });
});
