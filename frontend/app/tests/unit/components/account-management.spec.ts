import { mount, Wrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises/index';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AccountManagement from '@/components/AccountManagement.vue';
import { interop } from '@/electron-interop';
import { Api } from '@/plugins/api';
import { Interop } from '@/plugins/interop';
import store from '@/store/store';
import '../i18n';

jest.mock('@/electron-interop');
jest.mock('@/services/rotkehlchen-api');

Vue.use(Vuetify);
Vue.use(Api);
Vue.use(Interop);

describe('AccountManagement.vue', () => {
  let wrapper: Wrapper<AccountManagement>;

  beforeEach(() => {
    document.body.setAttribute('data-app', 'true');
    store.commit('setConnected', true);
    const vuetify = new Vuetify();
    wrapper = mount(AccountManagement, {
      store,
      vuetify,
      stubs: {
        VDialog: {
          template: '<span v-if="value"><slot></slot></span>',
          props: {
            value: { type: Boolean }
          }
        }
      },
      propsData: {
        logged: true
      }
    });
  });

  afterEach(() => {
    store.commit('session/reset');
  });

  describe('existing account', () => {
    test('non premium users should see the premium dialog', async () => {
      interop.premiumUserLoggedIn = jest.fn();
      store.dispatch = jest.fn().mockResolvedValue({ success: true });
      expect.assertions(4);
      // @ts-ignore
      await wrapper.vm.userLogin({ username: '1234', password: '1234' });
      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.premium-reminder').exists()).toBe(true);

      wrapper.find('.premium-reminder__buttons__confirm').trigger('click');

      await wrapper.vm.$nextTick();

      expect(wrapper.emitted()['login-complete']).toBeTruthy();
      expect(wrapper.emitted()['login-complete']).toHaveLength(1);
      expect(interop.premiumUserLoggedIn).toHaveBeenCalledWith(false);
    });

    test('premium users should not see the premium dialog', async () => {
      interop.premiumUserLoggedIn = jest.fn();
      store.commit('session/premium', true);
      store.dispatch = jest.fn().mockResolvedValue({ success: true });
      expect.assertions(4);
      // @ts-ignore
      await wrapper.vm.userLogin({ username: '1234', password: '1234' });
      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.premium-reminder').exists()).toBe(false);

      expect(wrapper.emitted()['login-complete']).toBeTruthy();
      expect(wrapper.emitted()['login-complete']).toHaveLength(1);
      expect(interop.premiumUserLoggedIn).toHaveBeenCalledWith(true);
    });
  });

  describe('new account', () => {
    test('non premium users should only see menu', async () => {
      interop.premiumUserLoggedIn = jest.fn();
      store.dispatch = jest.fn().mockResolvedValue({ success: true });
      expect.assertions(4);
      // @ts-ignore
      await wrapper.vm.createNewAccount({ username: '1234', password: '1234' });
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.premium-reminder').exists()).toBe(false);
      expect(wrapper.emitted()['login-complete']).toBeTruthy();
      expect(wrapper.emitted()['login-complete']).toHaveLength(1);
      expect(interop.premiumUserLoggedIn).toHaveBeenCalledWith(false);
    });

    test('premium users should not see the premium menu entry', async () => {
      expect.assertions(4);
      interop.premiumUserLoggedIn = jest.fn();
      store.dispatch = jest.fn().mockResolvedValue({ success: true });

      store.commit('session/premium', true);
      // @ts-ignore
      await wrapper.vm.createNewAccount({ username: '1234', password: '1234' });
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.premium-reminder').exists()).toBe(false);
      expect(wrapper.emitted()['login-complete']).toBeTruthy();
      expect(wrapper.emitted()['login-complete']).toHaveLength(1);
      expect(interop.premiumUserLoggedIn).toHaveBeenCalledWith(true);
    });
  });
});
