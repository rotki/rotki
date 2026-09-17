<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import ChainsUpdatedCaption from '@/modules/dashboard/components/ChainsUpdatedCaption.vue';
import DashboardRefresh from '@/modules/dashboard/components/DashboardRefresh.vue';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';

const { balanceDelta, busy, loadingNetWorth, netWorth, percentage } = defineProps<{
  netWorth: BigNumber;
  balanceDelta: BigNumber;
  /** The delta as a percentage string, or `-` when there is no starting value. */
  percentage: string;
  /** The first load has not produced a net worth yet. */
  loadingNetWorth: boolean;
  /** Any load is running, so the delta would move while it is read. */
  busy: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const indicator = computed<string>(() => {
  if (balanceDelta.isNegative())
    return 'lu-arrow-down';

  if (balanceDelta.isZero())
    return 'lu-git-commit-horizontal';

  return 'lu-arrow-up';
});

const balanceClass = computed<string>(() => {
  if (balanceDelta.isNegative())
    return '!text-rui-error-lighter';

  if (balanceDelta.isZero())
    return '!text-rui-grey-500';

  return '!text-rui-success';
});
</script>

<template>
  <div class="flex flex-col justify-start">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <div class="text-rui-text-secondary">
        {{ t('overall_balances.total_balance') }}
      </div>
      <DashboardRefresh />
    </div>
    <div
      class="font-medium"
      data-testid="overall-balances-net-worth"
    >
      <RuiSkeletonLoader
        v-if="loadingNetWorth"
        class="my-[0.5rem] w-56 h-[2rem] sm:my-[0.75rem] sm:w-72 sm:h-[2.5rem]"
        data-testid="overall-balances-net-worth-loading"
      />
      <FiatDisplay
        v-else
        class="text-[2rem] leading-[3rem] sm:text-[3rem] sm:leading-[4rem]"
        no-truncate
        :value="netWorth"
      />
    </div>

    <RuiSkeletonLoader
      v-if="busy"
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
