import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import ManualBalancesRefreshButton from '@/modules/accounts/manual-balances/ManualBalancesRefreshButton.vue';
import { ActivityKind } from '@/modules/task-center/core/types';

const refreshingBalances = ref<boolean>(false);
const refreshingPrices = ref<boolean>(false);
const calls: string[] = [];
const fetchManualBalances = vi.fn(async (): Promise<void> => {
  calls.push('balances');
});
const refreshPrices = vi.fn(async (): Promise<void> => {
  calls.push('prices');
});
const useIsActive = vi.fn(() => computed<boolean>(() => get(refreshingBalances)));

vi.mock('@/modules/balances/manual/use-manual-balances', () => ({
  useManualBalances: vi.fn(() => ({ fetchManualBalances })),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: vi.fn(() => ({ refreshing: computed<boolean>(() => get(refreshingPrices)), refreshPrices })),
}));

vi.mock('@/modules/task-center/use-task-center', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskCenter: vi.fn(() => ({ useIsActive })),
}));

const stubs = {
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean }, loading: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled" :data-loading="loading"><slot /></button>',
  },
  RuiButtonGroup: { template: '<div><slot /></div>' },
  RuiIcon: true,
  RuiMenu: {
    emits: ['update:modelValue'],
    props: { modelValue: { default: false, type: Boolean } },
    template: '<div data-testid="menu" :data-open="modelValue"><slot name="activator" :attrs="{ onClick: () => $emit(\'update:modelValue\', true) }" /><div><slot /></div></div>',
  },
};

function createWrapper(): VueWrapper<InstanceType<typeof ManualBalancesRefreshButton>> {
  return mount(ManualBalancesRefreshButton, { global: { stubs } });
}

describe('modules/accounts/manual-balances/ManualBalancesRefreshButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    calls.length = 0;
    set(refreshingBalances, false);
    set(refreshingPrices, false);
  });

  it('should refetch the manual balances, then their prices, from the main button', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=manual-balances-refresh]').trigger('click');
    await flushPromises();

    expect(fetchManualBalances).toHaveBeenCalledWith(true);
    expect(refreshPrices).toHaveBeenCalledWith(true);
    expect(calls).toEqual(['balances', 'prices']);
  });

  it('should refresh only the prices from the menu and close it', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=manual-balances-refresh-menu]').trigger('click');
    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('true');

    await wrapper.find('[data-testid=price-refresh]').trigger('click');

    expect(refreshPrices).toHaveBeenCalledWith(true);
    expect(fetchManualBalances).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('false');
  });

  it('should spin the main button while the manual balances load', async () => {
    const wrapper = createWrapper();

    expect(useIsActive).toHaveBeenCalledWith(ActivityKind.MANUAL_BALANCES);
    expect(wrapper.find('[data-testid=manual-balances-refresh]').attributes('data-loading')).toBe('false');

    set(refreshingBalances, true);
    await nextTick();

    expect(wrapper.find('[data-testid=manual-balances-refresh]').attributes('data-loading')).toBe('true');
  });

  it('should spin the main button and hold off the price refresh while prices load', async () => {
    const wrapper = createWrapper();
    set(refreshingPrices, true);
    await nextTick();

    expect(wrapper.find('[data-testid=manual-balances-refresh]').attributes('data-loading')).toBe('true');
    expect(wrapper.find('[data-testid=price-refresh]').attributes('disabled')).toBeDefined();
  });
});
