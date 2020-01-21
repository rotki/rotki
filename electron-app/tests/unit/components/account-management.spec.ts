import AccountManagement from '@/components/AccountManagement.vue';
import { mount, Wrapper } from '@vue/test-utils';
import store from '@/store/store';
import Vuetify from 'vuetify';
import Vue from 'vue';

Vue.use(Vuetify);

describe('AccountManagement.vue', () => {
  let vuetify: typeof Vuetify;
  let wrapper: Wrapper<AccountManagement>;

  beforeEach(() => {
    vuetify = new Vuetify();
    wrapper = mount(AccountManagement, {
      store,
      vuetify,
      attachToDocument: true,
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
      expect.assertions(3);
      // @ts-ignore
      wrapper.vm.firstStep();
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.account_management__premium').exists()).toBe(true);
      wrapper.find('.message-overlay__buttons__cancel').trigger('click');
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted()['login-complete']).toBeTruthy();
      expect(wrapper.emitted()['login-complete']).toHaveLength(1);
    });

    test('premium users should not see the premium dialog', async () => {
      expect.assertions(2);
      store.commit('session/premium', true);
      // @ts-ignore
      wrapper.vm.firstStep();
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted()['login-complete']).toBeTruthy();
      expect(wrapper.emitted()['login-complete']).toHaveLength(1);
    });
  });

  describe('new account', () => {
    test('non premium users should see the premium dialog', async () => {
      expect.assertions(4);
      store.commit('session/login', { username: 'test', newAccount: true });
      // @ts-ignore
      wrapper.vm.firstStep();
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.account_management__welcome').exists()).toBe(true);
      wrapper.find('.message-overlay__buttons__cancel').trigger('click');
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.account_management__premium').exists()).toBe(true);
      wrapper.find('.message-overlay__buttons__cancel').trigger('click');
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted()['login-complete']).toBeTruthy();
      expect(wrapper.emitted()['login-complete']).toHaveLength(1);
    });

    test('premium users should not see the premium dialog', async () => {
      expect.assertions(3);
      store.commit('session/premium', true);
      store.commit('session/login', { username: 'test', newAccount: true });
      // @ts-ignore
      wrapper.vm.firstStep();
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.account_management__welcome').exists()).toBe(true);

      wrapper.find('.message-overlay__buttons__cancel').trigger('click');
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted()['login-complete']).toBeTruthy();
      expect(wrapper.emitted()['login-complete']).toHaveLength(1);
    });
  });
});
