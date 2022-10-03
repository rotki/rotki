import { mount, Wrapper } from '@vue/test-utils';
import { set } from '@vueuse/core';
import {
  createPinia,
  PiniaVuePlugin,
  setActivePinia,
  storeToRefs
} from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import { usePremiumStore } from '@/store/session/premium';
import UserSecuritySettings from '@/views/settings/UserSecuritySettings.vue';
import '../../i18n';

vi.mock('@/services/backup', () => ({
  useBackupApi: () => ({
    info: vi.fn()
  })
}));

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

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
      ]
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
