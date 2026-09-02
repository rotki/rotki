import type { useLiquityStatistics } from '@/modules/staking/liquity/use-liquity-statistics';
import {
  type Balance,
  type BigNumber,
  bigNumberify,
  type LiquityStatisticDetails,
} from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type ShallowRef } from 'vue';
import { LUSD_ID } from '@/modules/staking/liquity/liquity-assets';
import { StatisticView } from '@/modules/staking/liquity/liquity-statistics';
import LiquityStatistics from '@/modules/staking/liquity/LiquityStatistics.vue';

interface StatsState {
  deposited: Balance | null;
  pnl: BigNumber | null;
  selection?: ShallowRef<StatisticView>;
  statistic: LiquityStatisticDetails | null;
}

const statsState = vi.hoisted((): StatsState => ({
  deposited: null,
  pnl: null,
  statistic: null,
}));

const BalanceDisplayStub = defineComponent({
  name: 'BalanceDisplayStub',
  props: { asset: { default: '', type: String }, loading: { default: false, type: Boolean }, value: { default: null, type: Object } },
  template: '<div />',
});

const PnlRowStub = defineComponent({
  name: 'LiquityPnlRowStub',
  props: { loading: { default: false, type: Boolean }, value: { default: null, type: Object } },
  template: '<div data-testid="pnl-row" />',
});

const AssetListStub = defineComponent({
  name: 'LiquityAssetBalanceListStub',
  props: { balances: { default: () => [], type: Array }, emptyLabel: { default: '', type: String }, loading: { default: false, type: Boolean } },
  template: '<div />',
});

vi.mock('@/modules/staking/liquity/use-liquity-statistics', async () => {
  const { computed, shallowRef: shallowRefFn } = await import('vue');
  return {
    useLiquityStatistics: (): ReturnType<typeof useLiquityStatistics> => {
      statsState.selection = shallowRefFn<StatisticView>(StatisticView.HISTORICAL);
      return {
        loading: computed(() => false),
        modelSelection: statsState.selection,
        statisticWithAdjustedPrice: computed(() => statsState.statistic),
        totalDepositedStabilityPoolBalance: computed(() => statsState.deposited),
        totalPnl: computed(() => statsState.pnl),
        totalWithdrawnStabilityPoolBalance: computed(() => null),
      };
    },
  };
});

function statistic(overrides: Partial<LiquityStatisticDetails> = {}): LiquityStatisticDetails {
  return {
    stabilityPoolGains: [],
    stakingGains: [],
    totalDepositedStabilityPool: bigNumberify(0),
    totalDepositedStabilityPoolValue: bigNumberify(0),
    totalValueGainsStabilityPool: bigNumberify(7),
    totalValueGainsStaking: bigNumberify(3),
    totalWithdrawnStabilityPool: bigNumberify(0),
    totalWithdrawnStabilityPoolValue: bigNumberify(0),
    ...overrides,
  };
}

describe('modules/staking/liquity/LiquityStatistics', () => {
  let wrapper: VueWrapper<InstanceType<typeof LiquityStatistics>>;

  /** The view model the mocked composable published, once the component has been mounted. */
  function viewModel(): ShallowRef<StatisticView> {
    const model = statsState.selection;
    if (!model)
      throw new Error('mount the component before reaching for its view model');

    return model;
  }

  function mountComponent(): VueWrapper<InstanceType<typeof LiquityStatistics>> {
    return mount(LiquityStatistics, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          BalanceDisplay: BalanceDisplayStub,
          FiatDisplay: { props: ['value', 'loading'], template: '<div />' },
          LiquityAssetBalanceList: AssetListStub,
          LiquityPnlRow: PnlRowStub,
          LiquityStatisticRow: { props: ['label'], template: '<div><slot /></div>' },
          RuiAccordion: { template: '<div><slot /></div>' },
          RuiAccordions: { template: '<div><slot /></div>' },
        },
      },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    statsState.deposited = null;
    statsState.pnl = null;
    statsState.statistic = null;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should say there is nothing to show without statistics', () => {
    wrapper = mountComponent();

    expect(wrapper.find('[data-testid=no-statistics]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=total-gains-staking]').exists()).toBe(false);
  });

  it('should show the totals once there are statistics', () => {
    statsState.statistic = statistic();

    wrapper = mountComponent();

    expect(wrapper.find('[data-testid=no-statistics]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=total-gains-stability-pool]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=total-gains-staking]').exists()).toBe(true);
  });

  it('should price the stability-pool totals in LUSD', () => {
    statsState.statistic = statistic();
    statsState.deposited = { amount: bigNumberify(1000), value: bigNumberify(1000) };

    wrapper = mountComponent();

    expect(wrapper.findComponent(BalanceDisplayStub).props('asset')).toBe(LUSD_ID);
  });

  it('should hide the profit row until there is a figure', () => {
    statsState.statistic = statistic();

    wrapper = mountComponent();

    expect(wrapper.findComponent(PnlRowStub).exists()).toBe(false);
  });

  it('should show the profit row once there is a figure', () => {
    statsState.statistic = statistic();
    statsState.pnl = bigNumberify(42);

    wrapper = mountComponent();

    expect(wrapper.findComponent(PnlRowStub).props('value')).toStrictEqual(bigNumberify(42));
  });

  it('should offer both views, bound to the shared model', () => {
    statsState.statistic = statistic();

    wrapper = mountComponent();

    expect(wrapper.find('[data-testid=view-current]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=view-historical]').exists()).toBe(true);
    expect(get(viewModel())).toBe(StatisticView.HISTORICAL);
  });
});
