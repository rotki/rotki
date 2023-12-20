import { type Wrapper, mount } from '@vue/test-utils';
import Vuetify from 'vuetify';
import UserSecuritySettings from '@/pages/settings/data-security/index.vue';

vi.mock('@/services/backup', () => ({
  useBackupApi: () => ({
    info: vi.fn()
  })
}));

describe('UserSecuritySettings.vue', () => {
  let wrapper: Wrapper<any>;

  function createWrapper() {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(UserSecuritySettings, {
      pinia,
      vuetify,
      stubs: [
        'v-tooltip',
        'card-title',
        'asset-select',
        'asset-update',
        'confirm-dialog',
        'data-table',
        'card'
      ],
      provide: {
        [Symbol.for('rui:table')]: {
          itemsPerPage: ref(10),
          globalItemsPerPage: false
        }
      }
    });
  }

  beforeEach(() => {
    wrapper = createWrapper();
  });

  test('displays no warning by default', async () => {
    expect(wrapper.find('[data-cy=premium-warning]').exists()).toBe(false);
  });

  test('displays warning if premium sync enabled', async () => {
    const { premiumSync } = storeToRefs(usePremiumStore());
    set(premiumSync, true);
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-cy=premium-warning]').exists()).toBe(true);
  });
});
