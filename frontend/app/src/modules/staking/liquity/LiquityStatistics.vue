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
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex items-center justify-between p-4">
        <h6 class="text-h6">
          {{ t('liquity_statistic.title') }}
        </h6>
        <RuiButtonGroup
          v-model="modelSelection"
          required
          variant="outlined"
          color="primary"
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
      <div class="grid md:grid-cols-2 gap-4 md:gap-12 text-lg">
        <div class="flex justify-between">
          <div class="text-rui-text-secondary">
            {{ t('liquity_statistic.total_gains_stability_pool') }}
          </div>
          <FiatDisplay
            :value="statisticWithAdjustedPrice.totalValueGainsStabilityPool"
            :loading="loading"
            class="font-bold"
            data-testid="total-gains-stability-pool"
          />
        </div>
        <div class="flex justify-between">
          <div class="text-rui-text-secondary">
            {{ t('liquity_statistic.total_gains_staking') }}
          </div>
          <FiatDisplay
            :value="statisticWithAdjustedPrice.totalValueGainsStaking"
            :loading="loading"
            class="font-bold"
            data-testid="total-gains-staking"
          />
        </div>
      </div>

      <RuiAccordions class="pt-4">
        <RuiAccordion
          :class-names="{ header: 'pt-4 pb-4 -mb-4 border-t border-default justify-center w-full' }"
          class="flex-col-reverse"
        >
          <div class="grid md:grid-cols-2 md:gap-12">
            <div>
              <LiquityStatisticRow
                :label="t('liquity_statistic.total_deposited_stability_pool')"
              >
                <BalanceDisplay
                  :asset="LUSD_ID"
                  :value="totalDepositedStabilityPoolBalance"
                  :loading="loading"
                  data-testid="total-deposited"
                />
              </LiquityStatisticRow>
              <LiquityStatisticRow
                :label="t('liquity_statistic.total_withdrawn_stability_pool')"
              >
                <BalanceDisplay
                  :asset="LUSD_ID"
                  :value="totalWithdrawnStabilityPoolBalance"
                  :loading="loading"
                  data-testid="total-withdrawn"
                />
              </LiquityStatisticRow>
              <LiquityStatisticRow
                :label="t('liquity_statistic.stability_pool_gains')"
              >
                <LiquityAssetBalanceList
                  :balances="statisticWithAdjustedPrice.stabilityPoolGains"
                  :loading="loading"
                  :empty-label="t('liquity_statistic.no_stability_pool_gains')"
                />
              </LiquityStatisticRow>
              <LiquityPnlRow
                v-if="totalPnl"
                :value="totalPnl"
                :loading="loading"
              />
            </div>
            <div>
              <LiquityStatisticRow
                :label="t('liquity_statistic.staking_gains')"
              >
                <LiquityAssetBalanceList
                  :balances="statisticWithAdjustedPrice.stakingGains"
                  :loading="loading"
                  :empty-label="t('liquity_statistic.no_staking_gains')"
                />
              </LiquityStatisticRow>
            </div>
          </div>
          <template #header="{ open }">
            <div class="text-rui-text-secondary mr-4 grow-0">
              {{ open ? t('liquity_statistic.view.hide') : t('liquity_statistic.view.show') }}
            </div>
          </template>
        </RuiAccordion>
      </RuiAccordions>
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
