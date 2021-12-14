import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, PiniaVuePlugin } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import { BackupApi } from '@/services/backup/backup-api';
import { api } from '@/services/rotkehlchen-api';
import store from '@/store/store';
import UserSecuritySettings from '@/views/settings/UserSecuritySettings.vue';
import { stub } from '../../../common/utils';
import '../../i18n';

jest.spyOn(api, 'backups', 'get').mockReturnValue(
  stub<BackupApi>({
    info: jest.fn()
  })
);

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

describe('UserSecuritySettings.vue', () => {
  let wrapper: Wrapper<any>;

  function createWrapper() {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    return mount(UserSecuritySettings, {
      store,
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
      mocks: {
        $api: {
          balances: {
            getPriceCache: () => []
          }
        },
        $interop: {
          isPackaged: () => true,
          config: () => ({
            logDirectory: ''
          })
        }
      }
    });
  }

  beforeEach(() => {
    wrapper = createWrapper();
  });

  test('displays no warning by default', async () => {
    expect(wrapper.find('.v-alert').exists()).toBe(false);
  });

  test('displays warning if premium sync enabled', async () => {
    store.commit('session/premiumSync', true);
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.v-alert').exists()).toBe(true);
  });
});
