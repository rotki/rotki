<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import BalanceViewPicker from '@/modules/balances/components/BalanceViewPicker.vue';
import { useBalanceViewData } from '@/modules/balances/view/use-balance-view-data';
import ChainsUpdatedCaption from '@/modules/dashboard/components/ChainsUpdatedCaption.vue';
import DashboardRefresh from '@/modules/dashboard/components/DashboardRefresh.vue';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';

/**
 * The dashboard's net worth, in the page's balance view.
 *
 * @remarks
 * In the history view the timeframe delta is replaced by the difference from the queried net worth:
 * the delta measures against queried snapshots, so against a history total it would be meaningless.
 * Both occupy the same one-line slot, so switching views moves nothing below it.
 */
const { balanceDelta, busy, loadingNetWorth, percentage } = defineProps<{
  balanceDelta: BigNumber;
  /** The delta as a percentage string, or `-` when there is no starting value. */
  percentage: string;
  /** The first load has not produced a net worth yet. */
  loadingNetWorth: boolean;
  /** Any load is running, so the delta would move while it is read. */
  busy: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { isHistory: historyView, netWorth, netWorthDifference } = useBalanceViewData();

const indicator = computed<string>(() => {
  if (balanceDelta.isNegative())
    return 'lu-arrow-down';

  if (balanceDelta.isZero())
    return 'lu-git-commit-horizontal';

  return 'lu-arrow-up';
});

const balanceClass = computed<string>(() => {
  if (balanceDelta.isNegative())
    return 'text-rui-error-lighter!';

  if (balanceDelta.isZero())
    return 'text-rui-grey-500!';

  return 'text-rui-success!';
});
</script>

<template>
  <div class="flex flex-col justify-start">
    <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
      <div class="flex items-center gap-1 text-rui-text-secondary">
        {{ t('overall_balances.total_balance') }}
        <BalanceViewPicker />
      </div>
      <DashboardRefresh />
    </div>
    <div
      class="font-medium"
      data-testid="overall-balances-net-worth"
    >
      <RuiSkeletonLoader
        v-if="loadingNetWorth"
        class="my-2 w-56 h-8 sm:my-3 sm:w-72 sm:h-10"
        data-testid="overall-balances-net-worth-loading"
      />
      <FiatDisplay
        v-else
        class="text-[2rem] leading-12 sm:text-[3rem] sm:leading-16"
        no-truncate
        :value="netWorth"
      />
    </div>

    <div
      v-if="historyView"
      class="flex items-center gap-2 h-6 font-medium whitespace-nowrap"
      data-testid="overall-balances-history-difference"
    >
      <RuiIcon
        name="lu-history"
        size="16"
        class="text-rui-text-secondary"
      />
      <span class="text-rui-text-secondary font-normal">{{ t('balance_view.vs_queried') }}</span>
      <FiatDisplay
        :class="{ 'text-rui-warning': !netWorthDifference.isZero() }"
        :value="netWorthDifference"
      />
    </div>
    <RuiSkeletonLoader
      v-else-if="busy"
      class="w-48 h-6"
      data-testid="overall-balances-delta-loading"
    />
    <div
      v-else
      :class="balanceClass"
      class="flex items-center gap-2 rounded-full font-medium"
    >
      <RuiIcon
        :name="indicator"
        size="16"
      />
      <PercentageDisplay
        class="pr-4"
        :value="percentage"
      />
      <span class="whitespace-nowrap before:content-['('] after:content-[')']">
        <FiatDisplay :value="balanceDelta" />
      </span>
    </div>

    <ChainsUpdatedCaption class="mt-2" />
  </div>
</template>
