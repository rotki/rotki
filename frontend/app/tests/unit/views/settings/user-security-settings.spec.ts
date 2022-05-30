import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import { BackupApi } from '@/services/backup/backup-api';
import { api } from '@/services/rotkehlchen-api';
import store from '@/store/store';
import UserSecuritySettings from '@/views/settings/UserSecuritySettings.vue';
import { stub } from '../../../common/utils';
import '../../i18n';

vi.spyOn(api, 'backups', 'get').mockReturnValue(
  stub<BackupApi>({
    info: vi.fn()
  })
);

Vue.use(Vuetify);

describe('UserSecuritySettings.vue', () => {
  let wrapper: Wrapper<any>;

  function createWrapper() {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(UserSecuritySettings, {
      store,
      pinia,
      provide: {
        'vuex-store': store
      },
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
    expect(wrapper.find('[data-cy=premium-warning]').exists()).toBe(false);
  });

  test('displays warning if premium sync enabled', async () => {
    store.commit('session/premiumSync', true);
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-cy=premium-warning]').exists()).toBe(true);
  });
});
