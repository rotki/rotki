import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref, ref } from 'vue';
import ExchangeKeysFormDialog from '@/modules/settings/api-keys/exchange/ExchangeKeysFormDialog.vue';
import Exchanges from '@/pages/api-keys/exchanges/index.vue';
import '@test/i18n';

vi.mock('vue-router', () => ({
  useRouter: (): Record<string, unknown> => ({ push: vi.fn(), replace: vi.fn() }),
  useRoute: (): Ref<{ query: Record<string, unknown> }> => ref({ query: {} }),
}));

vi.mock('@/modules/balances/exchanges/use-exchanges', () => ({
  useExchanges: (): Record<string, unknown> => ({ removeExchange: vi.fn() }),
}));

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): Record<string, unknown> => ({ getExchangeName: (location: string): string => location }),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): Record<string, unknown> => ({ notify: vi.fn() }),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): Record<string, unknown> => ({ update: vi.fn() }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<unknown[]> => ref([]),
}));

const HINT = '[data-testid=exchange-setup-hint]';

describe('exchanges page', () => {
  let wrapper: VueWrapper<InstanceType<typeof Exchanges>>;
  let pinia: Pinia;

  function createWrapper(): VueWrapper<InstanceType<typeof Exchanges>> {
    return mount(Exchanges, {
      global: {
        plugins: [pinia],
        stubs: {
          RouterLink: true,
          Teleport: { template: '<span><slot /></span>' },
          Transition: { template: '<span><slot /></span>' },
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
          HintMenuIcon: true,
          ExternalLink: true,
          LocationDisplay: true,
          RowActions: true,
          RuiDataTable: true,
          ExchangeKeysFormDialog: true,
        },
      },
    });
  }

  async function addExchange(): Promise<void> {
    await wrapper
      .findComponent(ExchangeKeysFormDialog)
      .vm
      .$emit('added', { location: 'kraken', name: 'main' });
    await nextTick();
  }

  beforeEach(() => {
    document.body.dataset.app = 'true';
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    wrapper?.unmount();
  });

  it('should not show the setup hint before an exchange is added', async () => {
    wrapper = createWrapper();
    await flushPromises();
    expect(wrapper.find(HINT).exists()).toBe(false);
  });

  it('should show the setup hint when an exchange is added', async () => {
    wrapper = createWrapper();
    await flushPromises();
    await addExchange();
    const hint = wrapper.find(HINT);
    expect(hint.exists()).toBe(true);
    expect(hint.text()).toContain('exchange_settings.setup_hint');
  });

  it('should hide the setup hint when dismissed', async () => {
    wrapper = createWrapper();
    await flushPromises();
    await addExchange();
    expect(wrapper.find(HINT).exists()).toBe(true);

    await wrapper.find(`${HINT} button`).trigger('click');
    await nextTick();
    expect(wrapper.find(HINT).exists()).toBe(false);
  });

  it('should auto-hide the setup hint after the timeout', async () => {
    wrapper = createWrapper();
    await flushPromises();
    await addExchange();
    expect(wrapper.find(HINT).exists()).toBe(true);

    vi.advanceTimersByTime(9000);
    await nextTick();
    expect(wrapper.find(HINT).exists()).toBe(false);
  });
});
