import { type VueWrapper, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import UserSecuritySettings from '@/pages/settings/data-security/index.vue';
import { libraryDefaults } from '../../../utils/provide-defaults';

vi.mock('vue-router', () => ({
  useRoute: vi.fn(),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(),
  }),
  createRouter: vi.fn().mockImplementation(() => ({
    beforeEach: vi.fn(),
  })),
  createWebHashHistory: vi.fn(),
}));

describe('userSecuritySettings.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof UserSecuritySettings>>;

  function createWrapper() {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(UserSecuritySettings, {
      global: {
        plugins: [pinia],
        stubs: ['card-title', 'asset-select', 'asset-update', 'confirm-dialog', 'data-table'],
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
