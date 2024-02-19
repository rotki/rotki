import { type VueWrapper, mount } from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import UserSecuritySettings from '@/pages/settings/data-security/index.vue';
import { libraryDefaults } from '../../../utils/provide-defaults';

vi.mock('@/services/backup', () => ({
  useBackupApi: () => ({
    info: vi.fn(),
  }),
}));

describe('userSecuritySettings.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof UserSecuritySettings>>;

  function createWrapper() {
    const vuetify = createVuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(UserSecuritySettings, {
      global: {
        plugins: [pinia, vuetify],
        stubs: [
          'v-tooltip',
          'card-title',
          'asset-select',
          'asset-update',
          'confirm-dialog',
          'data-table',
          'card',
        ],
        provide: libraryDefaults,
      },

    });
  }

  beforeEach(() => {
    wrapper = createWrapper();
  });

  it('displays no warning by default', async () => {
    expect(wrapper.find('[data-cy=premium-warning]').exists()).toBe(false);
  });

  it('displays warning if premium sync enabled', async () => {
    const { premiumSync } = storeToRefs(usePremiumStore());
    set(premiumSync, true);
    await nextTick();
    expect(wrapper.find('[data-cy=premium-warning]').exists()).toBe(true);
  });
});
