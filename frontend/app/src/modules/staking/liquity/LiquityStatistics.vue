<script setup lang="ts">
import type { LiquityPoolDetailEntry, LiquityStatisticDetails } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import { LUSD_ID } from '@/modules/staking/liquity/liquity-assets';
import { StatisticView } from '@/modules/staking/liquity/liquity-statistics';
import LiquityAssetBalanceList from '@/modules/staking/liquity/LiquityAssetBalanceList.vue';
import LiquityPnlRow from '@/modules/staking/liquity/LiquityPnlRow.vue';
import LiquityStatisticRow from '@/modules/staking/liquity/LiquityStatisticRow.vue';
import { useLiquityStatistics } from '@/modules/staking/liquity/use-liquity-statistics';

const { pool = null, statistic = null } = defineProps<{
  statistic?: LiquityStatisticDetails | null;
  pool?: LiquityPoolDetailEntry | null;
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  loading,
  modelSelection,
  statisticWithAdjustedPrice,
  totalDepositedStabilityPoolBalance,
  totalPnl,
  totalWithdrawnStabilityPoolBalance,
} = useLiquityStatistics({
  pool: () => pool,
  statistic: () => statistic,
});

const showDetails = ref<boolean>(false);
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5">
        <h6 class="text-base font-semibold text-rui-text">
          {{ t('liquity_statistic.title') }}
        </h6>
        <RuiButtonGroup
          v-model="modelSelection"
          variant="segmented"
          required
        >
          <RuiButton
            :model-value="StatisticView.CURRENT"
            data-testid="view-current"
          >
            {{ t('liquity_statistic.switch.current') }}
          </RuiButton>
          <RuiButton
            :model-value="StatisticView.HISTORICAL"
            data-testid="view-historical"
          >
            {{ t('liquity_statistic.switch.historical') }}
          </RuiButton>
        </RuiButtonGroup>
      </div>
    </template>
    <template v-if="statisticWithAdjustedPrice">
      <div class="grid md:grid-cols-2 gap-4">
        <div>
          <div class="text-sm text-rui-text-secondary">
            {{ t('liquity_statistic.total_gains_stability_pool') }}
          </div>
          <FiatDisplay
            :value="statisticWithAdjustedPrice.totalValueGainsStabilityPool"
            :loading="loading"
            class="text-h5 font-semibold"
            data-testid="total-gains-stability-pool"
          />
        </div>
        <div>
          <div class="text-sm text-rui-text-secondary">
            {{ t('liquity_statistic.total_gains_staking') }}
          </div>
          <FiatDisplay
            :value="statisticWithAdjustedPrice.totalValueGainsStaking"
            :loading="loading"
            class="text-h5 font-semibold"
            data-testid="total-gains-staking"
          />
        </div>
      </div>

      <div
        v-if="showDetails"
        class="grid md:grid-cols-2 md:gap-x-12 mt-4"
        data-testid="statistics-details"
      >
        <div>
          <LiquityStatisticRow :label="t('liquity_statistic.total_deposited_stability_pool')">
            <BalanceDisplay
              :asset="LUSD_ID"
              :value="totalDepositedStabilityPoolBalance"
              :loading="loading"
              data-testid="total-deposited"
            />
          </LiquityStatisticRow>
          <LiquityStatisticRow :label="t('liquity_statistic.total_withdrawn_stability_pool')">
            <BalanceDisplay
              :asset="LUSD_ID"
              :value="totalWithdrawnStabilityPoolBalance"
              :loading="loading"
              data-testid="total-withdrawn"
            />
          </LiquityStatisticRow>
          <LiquityStatisticRow :label="t('liquity_statistic.stability_pool_gains')">
            <LiquityAssetBalanceList
              :balances="statisticWithAdjustedPrice.stabilityPoolGains"
              :loading="loading"
              :empty-label="t('liquity_statistic.none')"
            />
          </LiquityStatisticRow>
          <LiquityPnlRow
            v-if="totalPnl"
            :value="totalPnl"
            :loading="loading"
          />
        </div>
        <div>
          <LiquityStatisticRow :label="t('liquity_statistic.staking_gains')">
            <LiquityAssetBalanceList
              :balances="statisticWithAdjustedPrice.stakingGains"
              :loading="loading"
              :empty-label="t('liquity_statistic.none')"
            />
          </LiquityStatisticRow>
        </div>
      </div>

      <RuiButton
        variant="text"
        size="sm"
        class="mt-3 -ml-2"
        data-testid="statistics-details-toggle"
        @click="showDetails = !showDetails"
      >
        {{ showDetails ? t('liquity_statistic.view.hide') : t('liquity_statistic.view.show') }}
        <template #append>
          <RuiIcon
            :name="showDetails ? 'lu-chevron-up' : 'lu-chevron-down'"
            size="16"
          />
        </template>
      </RuiButton>
    </template>
    <div
      v-else
      class="text-center text-rui-text-secondary pb-4"
      data-testid="no-statistics"
    >
      {{ t('liquity_statistic.no_statistics') }}
    </div>
  </RuiCard>
</template>
