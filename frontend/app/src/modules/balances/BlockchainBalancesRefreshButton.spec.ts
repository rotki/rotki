import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import BlockchainBalancesRefreshButton from '@/modules/balances/BlockchainBalancesRefreshButton.vue';

const isRefreshing = ref<boolean>(false);
const isDetectingTokens = ref<boolean>(false);
const refreshDisabled = ref<boolean>(false);
const refreshingPrices = ref<boolean>(false);
const loadingBalances = ref<boolean>(false);
const refreshPrices = vi.fn(async (): Promise<void> => {});
const refreshBlockchainAndPrices = vi.fn(async (): Promise<void> => {});

vi.mock('@/modules/balances/use-balance-status', () => ({
  useBalanceStatus: vi.fn(() => ({ isRefreshing: computed<boolean>(() => get(isRefreshing)) })),
}));

vi.mock('@/modules/accounts/use-blockchain-account-loading', () => ({
  useBlockchainAccountLoading: vi.fn(() => ({
    isDetectingTokens: computed<boolean>(() => get(isDetectingTokens)),
    refreshDisabled: computed<boolean>(() => get(refreshDisabled)),
  })),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: vi.fn(() => ({ refreshing: computed<boolean>(() => get(refreshingPrices)), refreshPrices })),
}));

vi.mock('@/modules/balances/use-balance-loading', () => ({
  useBalancesLoading: vi.fn(() => ({ loadingBalances: computed<boolean>(() => get(loadingBalances)) })),
}));

vi.mock('@/modules/balances/use-balance-refresh', () => ({
  useBalanceRefresh: vi.fn(() => ({ refreshBlockchainAndPrices })),
}));

const stubs = {
  BlockchainBalanceRefreshBehaviourMenu: { template: '<div data-testid="behaviour-menu" />' },
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean }, loading: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled" :data-loading="loading"><slot /></button>',
  },
  RuiButtonGroup: { template: '<div><slot /></div>' },
  RuiDivider: true,
  RuiIcon: true,
  RuiMenu: {
    emits: ['update:modelValue'],
    props: { modelValue: { default: false, type: Boolean } },
    template: '<div data-testid="menu" :data-open="modelValue"><slot name="activator" :attrs="{ onClick: () => $emit(\'update:modelValue\', true) }" /><div><slot /></div></div>',
  },
};

function createWrapper(): VueWrapper<InstanceType<typeof BlockchainBalancesRefreshButton>> {
  return mount(BlockchainBalancesRefreshButton, { global: { stubs } });
}

describe('modules/balances/BlockchainBalancesRefreshButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(isRefreshing, false);
    set(isDetectingTokens, false);
    set(refreshDisabled, false);
    set(refreshingPrices, false);
    set(loadingBalances, false);
  });

  it('should refresh the balances and the prices from the main button', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=blockchain-balances-refresh]').trigger('click');

    expect(refreshBlockchainAndPrices).toHaveBeenCalledOnce();
    expect(refreshPrices).not.toHaveBeenCalled();
  });

  it('should refresh only the prices from the menu, skipping the cache, and close it', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=blockchain-balances-refresh-menu]').trigger('click');
    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('true');

    await wrapper.find('[data-testid=price-refresh]').trigger('click');

    expect(refreshPrices).toHaveBeenCalledWith(true);
    expect(refreshBlockchainAndPrices).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('false');
  });

  it.each([
    ['balances refresh', isRefreshing],
    ['token detection', isDetectingTokens],
    ['price refresh', refreshingPrices],
  ])('should spin the main button during a %s', async (_, state) => {
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=blockchain-balances-refresh]').attributes('data-loading')).toBe('false');

    set(state, true);
    await nextTick();

    expect(wrapper.find('[data-testid=blockchain-balances-refresh]').attributes('data-loading')).toBe('true');
  });

  it('should disable the main button while a refresh cannot start', async () => {
    const wrapper = createWrapper();
    set(refreshDisabled, true);
    await nextTick();

    expect(wrapper.find('[data-testid=blockchain-balances-refresh]').attributes('disabled')).toBeDefined();
  });

  it('should hold off the price refresh while prices or balances load', async () => {
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=price-refresh]').attributes('disabled')).toBeUndefined();

    set(loadingBalances, true);
    await nextTick();
    expect(wrapper.find('[data-testid=price-refresh]').attributes('disabled')).toBeDefined();

    set(loadingBalances, false);
    set(refreshingPrices, true);
    await nextTick();
    expect(wrapper.find('[data-testid=price-refresh]').attributes('disabled')).toBeDefined();
  });

  it('should keep the refresh behaviour settings in the menu', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=behaviour-menu]').exists()).toBe(true);
  });
});
