<script setup lang="ts">
import {
  type LiquityPoolDetailEntry,
  type LiquityStatisticDetails
} from '@rotki/common/lib/liquity';
import { type ComputedRef, type Ref } from 'vue';
import { type AssetBalance, type Balance, type BigNumber } from '@rotki/common';
import { Section } from '@/types/status';
import { CURRENCY_USD } from '@/types/currencies';

const props = withDefaults(
  defineProps<{
    statistic?: LiquityStatisticDetails | null;
    pool?: LiquityPoolDetailEntry | null;
  }>(),
  {
    statistic: null,
    pool: null
  }
);

const { statistic, pool } = toRefs(props);
const { assetPrice } = useBalancePricesStore();
const LUSD_ID = 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0';
const lusdPrice = assetPrice(LUSD_ID);

const { t } = useI18n();

const { isLoading } = useStatusStore();
const loading = isLoading(Section.DEFI_LIQUITY_STATISTICS);

const current: Ref<boolean> = ref(false);

const statisticWithAdjustedPrice: ComputedRef<LiquityStatisticDetails | null> =
  computed(() => {
    const statisticVal = get(statistic);

    if (!statisticVal) {
      return null;
    }

    if (!get(current)) {
      return statisticVal;
    }

    const stakingGains = statisticVal.stakingGains.map(
      (stakingGain: AssetBalance) => {
        const price = get(assetPrice(stakingGain.asset)) ?? One;

        return {
          ...stakingGain,
          usdValue: stakingGain.amount.multipliedBy(price)
        };
      }
    );

    const stabilityPoolGains = statisticVal.stabilityPoolGains.map(
      (stabilityPoolGain: AssetBalance) => {
        const price = get(assetPrice(stabilityPoolGain.asset)) ?? One;

        return {
          ...stabilityPoolGain,
          usdValue: stabilityPoolGain.amount.multipliedBy(price)
        };
      }
    );

    const totalUsdGainsStabilityPool = bigNumberSum(
      stabilityPoolGains.map(({ usdValue }) => usdValue)
    );

    const totalUsdGainsStaking = bigNumberSum(
      stakingGains.map(({ usdValue }) => usdValue)
    );

    return {
      ...statisticVal,
      totalUsdGainsStabilityPool,
      totalUsdGainsStaking,
      totalDepositedStabilityPoolUsdValue:
        statisticVal.totalDepositedStabilityPool.multipliedBy(
          get(lusdPrice) ?? One
        ),
      totalWithdrawnStabilityPoolUsdValue:
        statisticVal.totalWithdrawnStabilityPool.multipliedBy(
          get(lusdPrice) ?? One
        ),
      stakingGains,
      stabilityPoolGains
    };
  });

const totalDepositedStabilityPoolBalance = useRefMap<
  LiquityStatisticDetails | null,
  Balance | null
>(statisticWithAdjustedPrice, data => {
  if (!data) {
    return null;
  }

  return {
    amount: data.totalDepositedStabilityPool,
    usdValue: data.totalDepositedStabilityPoolUsdValue
  };
});

const totalWithdrawnStabilityPoolBalance = useRefMap<
  LiquityStatisticDetails | null,
  Balance | null
>(statisticWithAdjustedPrice, data => {
  if (!data) {
    return null;
  }

  return {
    amount: data.totalWithdrawnStabilityPool,
    usdValue: data.totalWithdrawnStabilityPoolUsdValue
  };
});

/**
 * Calculate the estimated PnL, by finding difference between these two things:
 * - Total LUSD that user have lost in stability pool, and find the current price.
 * - Current price of all asset user have now + total gains from the stability pool.
 *
 * The calculation:
 * A = Total Deposited Stability Pool - Total Withdrawn Stability Pool
 * LG = Liquidity gains in current price.
 * R = Rewards incurrent price.
 * B = Total Gains Stability Pool + LG + R
 * C = (A - Current deposited amount) in current price
 * PnL = B - C
 *
 * @param totalDepositedStabilityPool
 * @param totalWithdrawnStabilityPool
 * @param totalUsdGainsStabilityPool
 * @param poolGains
 * @param poolRewards
 * @param poolDeposited
 * @return BigNumber
 */
const calculatePnl = (
  totalDepositedStabilityPool: BigNumber,
  totalWithdrawnStabilityPool: BigNumber,
  totalUsdGainsStabilityPool: BigNumber,
  poolGains: AssetBalance,
  poolRewards: AssetBalance,
  poolDeposited: AssetBalance
): ComputedRef<BigNumber> =>
  computed(() => {
    const expectedAmount = totalDepositedStabilityPool.minus(
      totalWithdrawnStabilityPool
    );

    const liquidationGainsInCurrentPrice = poolGains.amount.multipliedBy(
      get(assetPrice(poolGains.asset)) ?? One
    );

    const rewardsInCurrentPrice = poolRewards.amount.multipliedBy(
      get(assetPrice(poolRewards.asset)) ?? One
    );

    const totalWithdrawals = totalUsdGainsStabilityPool
      .plus(liquidationGainsInCurrentPrice)
      .plus(rewardsInCurrentPrice);

    const diffDeposited = expectedAmount.minus(poolDeposited.amount);

    const diffDepositedInCurrentUsdPrice = diffDeposited.multipliedBy(
      get(lusdPrice) ?? One
    );

    return totalWithdrawals.minus(diffDepositedInCurrentUsdPrice);
  });

const totalPnl: ComputedRef<BigNumber | null> = computed(() => {
  const statisticVal = get(statistic);
  const poolVal = get(pool);

  if (!statisticVal || !poolVal) {
    return null;
  }

  return get(
    calculatePnl(
      statisticVal.totalDepositedStabilityPool,
      statisticVal.totalWithdrawnStabilityPool,
      statisticVal.totalUsdGainsStabilityPool,
      poolVal.gains,
      poolVal.rewards,
      poolVal.deposited
    )
  );
});

const css = useCssModule();
</script>

<template>
  <Card :loading="loading">
    <template #title>
      {{ t('liquity_statistic.title') }}
    </template>
    <template #details>
      <VBtnToggle v-model="current" dense mandatory>
        <RuiButton :value="true">
          {{ t('liquity_statistic.switch.current') }}
        </RuiButton>
        <RuiButton :value="false">
          {{ t('liquity_statistic.switch.historical') }}
        </RuiButton>
      </VBtnToggle>
    </template>
    <template v-if="statisticWithAdjustedPrice">
      <VRow class="ma-n6" :class="css.large">
        <VCol md="6" class="pa-6 py-8 flex justify-between">
          <div>{{ t('liquity_statistic.total_gains_stability_pool') }}</div>
          <VSheet>
            <AmountDisplay
              :value="statisticWithAdjustedPrice.totalUsdGainsStabilityPool"
              :fiat-currency="CURRENCY_USD"
              class="font-bold"
            />
          </VSheet>
        </VCol>
        <VCol md="6" class="pa-6 py-8 flex justify-between">
          <div>{{ t('liquity_statistic.total_gains_staking') }}</div>
          <VSheet>
            <AmountDisplay
              :value="statisticWithAdjustedPrice.totalUsdGainsStaking"
              :fiat-currency="CURRENCY_USD"
              class="font-bold"
            />
          </VSheet>
        </VCol>
      </VRow>

      <VExpansionPanels multiple class="pt-4">
        <VExpansionPanel elevation="0">
          <VExpansionPanelContent>
            <VRow class="ma-n6">
              <VCol md="6" class="pa-6">
                <div>
                  <VDivider />
                  <div class="text-right py-4">
                    <div class="font-medium pb-2" :class="css.label">
                      {{
                        t('liquity_statistic.total_deposited_stability_pool')
                      }}
                    </div>
                    <BalanceDisplay
                      :asset="LUSD_ID"
                      :value="totalDepositedStabilityPoolBalance"
                    />
                  </div>
                </div>

                <div>
                  <VDivider />
                  <div class="text-right py-4">
                    <div class="font-medium pb-2" :class="css.label">
                      {{
                        t('liquity_statistic.total_withdrawn_stability_pool')
                      }}
                    </div>
                    <BalanceDisplay
                      :asset="LUSD_ID"
                      :value="totalWithdrawnStabilityPoolBalance"
                    />
                  </div>
                </div>

                <div>
                  <VDivider />
                  <div class="text-right py-4">
                    <div class="font-medium pb-2" :class="css.label">
                      {{ t('liquity_statistic.stability_pool_gains') }}
                    </div>

                    <div
                      v-if="
                        statisticWithAdjustedPrice.stabilityPoolGains.length > 0
                      "
                    >
                      <div
                        v-for="assetBalance in statisticWithAdjustedPrice.stabilityPoolGains"
                        :key="assetBalance.asset"
                      >
                        <BalanceDisplay
                          :asset="assetBalance.asset"
                          :value="assetBalance"
                        />
                      </div>
                    </div>
                    <div v-else class="grey--text pb-2">
                      {{ t('liquity_statistic.no_stability_pool_gains') }}
                    </div>
                  </div>
                </div>

                <div v-if="totalPnl">
                  <VDivider />
                  <div class="text-right py-4">
                    <div class="font-medium pb-2" :class="css.label">
                      <VTooltip open-delay="400" top>
                        <template #activator="{ on, attrs }">
                          <VIcon v-bind="attrs" small class="mx-2" v-on="on">
                            mdi-information
                          </VIcon>
                        </template>
                        <span>
                          {{ t('liquity_statistic.estimated_pnl_warning') }}
                        </span>
                      </VTooltip>
                      {{ t('liquity_statistic.estimated_pnl') }}
                    </div>
                    <AmountDisplay
                      :value="totalPnl"
                      :fiat-currency="CURRENCY_USD"
                      pnl
                    />
                  </div>
                </div>
              </VCol>
              <VCol md="6" class="pa-6">
                <div>
                  <VDivider />
                  <div class="text-right py-4">
                    <div class="font-medium pb-2" :class="css.label">
                      {{ t('liquity_statistic.staking_gains') }}
                    </div>

                    <div
                      v-if="statisticWithAdjustedPrice.stakingGains.length > 0"
                    >
                      <div
                        v-for="assetBalance in statisticWithAdjustedPrice.stakingGains"
                        :key="assetBalance.asset"
                      >
                        <BalanceDisplay
                          :asset="assetBalance.asset"
                          :value="assetBalance"
                        />
                      </div>
                    </div>
                    <div v-else class="grey--text pb-2">
                      {{ t('liquity_statistic.no_staking_gains') }}
                    </div>
                  </div>
                </div>
              </VCol>
            </VRow>
          </VExpansionPanelContent>
          <VDivider />
          <VExpansionPanelHeader class="flex justify-center w-full">
            <template #default="{ open }">
              <div class="grey--text mr-4 grow-0" :class="css.large">
                {{
                  open
                    ? t('liquity_statistic.view.hide')
                    : t('liquity_statistic.view.show')
                }}
              </div>
            </template>
          </VExpansionPanelHeader>
        </VExpansionPanel>
      </VExpansionPanels>
    </template>
    <div v-else class="text-center grey--text pt-4 pb-2">
      {{ t('liquity_statistic.no_statistics') }}
    </div>
  </Card>
</template>

<style lang="scss" module>
.large {
  font-size: 1.2rem;
}

.label {
  font-size: 1.1rem;
}

:global {
  .v-expansion-panel {
    background: transparent !important;

    &::before {
      box-shadow: none;
    }

    &-header {
      padding: 1rem 0 0.25rem;
      min-height: auto !important;
      display: flex;
      justify-content: center;

      &__icon {
        margin-left: 0 !important;
      }
    }

    &-content {
      &__wrap {
        padding: 0;
      }
    }
  }
}
</style>
