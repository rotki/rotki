import { createTestingPinia } from '@pinia/testing';
import { mount, Wrapper } from '@vue/test-utils';
import { set } from '@vueuse/core';
import flushPromises from 'flush-promises/index';
import { setActivePinia, storeToRefs } from 'pinia';
import Vuetify from 'vuetify';
import { VDialog } from 'vuetify/lib/components';
import AccountManagement from '@/components/AccountManagement.vue';
import { setupLiquidityPosition } from '@/composables/defi';
import { interop, useInterop } from '@/electron-interop';
import { useAggregatedBalancesStore } from '@/store/balances/aggregated';
import { useMainStore } from '@/store/main';
import { useSessionStore } from '@/store/session';
import { usePremiumStore } from '@/store/session/premium';
import { bigNumberify } from '@/utils/bignumbers';

vi.mock('@/electron-interop');
vi.mock('@/services/rotkehlchen-api');
vi.mock('@/composables/defi');

// This is workaround used because stubs is somehow not working,
// Eager prop will render the <slot /> immediately
// @ts-ignore
VDialog.options.props.eager.default = true;

describe('AccountManagement.vue', () => {
  let wrapper: Wrapper<any>;
  let sessionStore: ReturnType<typeof useSessionStore>;

  beforeEach(() => {
    document.body.setAttribute('data-app', 'true');
    const vuetify = new Vuetify();

    (useInterop as any).mockImplementation(() => interop);
    interop.premiumUserLoggedIn = vi.fn();

    const testingPinia = createTestingPinia();
    setActivePinia(testingPinia);

    useMainStore(testingPinia).connected = true;
    (setupLiquidityPosition as any).mockImplementation(() => ({
      lpTotal: () => bigNumberify(0),
      lpAggregatedBalances: () => []
    }));

    useAggregatedBalancesStore(testingPinia).balances = () => [];
    useAggregatedBalancesStore(testingPinia).liabilities = () => [];

    sessionStore = useSessionStore();

    wrapper = mount(AccountManagement, {
      pinia: testingPinia,
      vuetify,
      propsData: {
        logged: true
      }
    });
  });

  describe('existing account', () => {
    test('non premium users should see the premium dialog', async () => {
      (sessionStore.login as any).mockResolvedValue({
        success: true
      });
      expect.assertions(4);
      // @ts-ignore
      await wrapper.vm.userLogin({ username: '1234', password: '1234' });
      await flushPromises();
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.premium-reminder').exists()).toBe(true);

      await wrapper
        .find('.premium-reminder__buttons__confirm')
        .trigger('click');

      await wrapper.vm.$nextTick();

      expect(wrapper.emitted()['login-complete']).toBeTruthy();
      expect(wrapper.emitted()['login-complete']).toHaveLength(1);
      expect(interop.premiumUserLoggedIn).toHaveBeenCalledWith(false);
    });

    test('premium users should not see the premium dialog', async () => {
      (sessionStore.login as any).mockResolvedValue({
        success: true
      });
      const { premium } = storeToRefs(usePremiumStore());
      set(premium, true);
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
      (sessionStore.createAccount as any).mockResolvedValue({ success: true });
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
      (sessionStore.createAccount as any).mockResolvedValue({ success: true });
      expect.assertions(4);
      const { premium } = storeToRefs(usePremiumStore());
      set(premium, true);
      // @ts-ignore
      await wrapper.vm.createNewAccount({ username: '1234', password: '1234' });
      await wrapper.vm.$nextTick();
      await flushPromises();

      expect(wrapper.find('.premium-reminder').exists()).toBe(false);
      expect(wrapper.emitted()['login-complete']).toBeTruthy();
      expect(wrapper.emitted()['login-complete']).toHaveLength(1);
      expect(interop.premiumUserLoggedIn).toHaveBeenCalledWith(true);
    });
  });
});
