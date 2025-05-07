<script setup lang="ts">
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import { useRefMap } from '@/composables/utils/useRefMap';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useStatusStore } from '@/store/status';
import { CURRENCY_USD } from '@/types/currencies';
import { Section } from '@/types/status';
import { bigNumberSum } from '@/utils/calculation';
import { type AssetBalance, type Balance, type BigNumber, type LiquityPoolDetailEntry, type LiquityStatisticDetails, One } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    statistic?: LiquityStatisticDetails | null;
    pool?: LiquityPoolDetailEntry | null;
  }>(),
  {
    pool: null,
    statistic: null,
  },
);

const { pool, statistic } = toRefs(props);
const { assetPrice } = usePriceUtils();
const LUSD_ID = 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0';
const lusdPrice = assetPrice(LUSD_ID);

const { t } = useI18n({ useScope: 'global' });

const { isLoading } = useStatusStore();
const loading = isLoading(Section.DEFI_LIQUITY_STATISTICS);

const selection = ref<'historical' | 'current'>('historical');

const statisticWithAdjustedPrice = computed<LiquityStatisticDetails | null>(() => {
  const statisticVal = get(statistic);

  if (!statisticVal)
    return null;

  if (get(selection) === 'historical')
    return statisticVal;

  const stakingGains = statisticVal.stakingGains.map((stakingGain: AssetBalance) => {
    const price = get(assetPrice(stakingGain.asset)) ?? One;

    return {
      ...stakingGain,
      usdValue: stakingGain.amount.multipliedBy(price),
    };
  });

  const stabilityPoolGains = statisticVal.stabilityPoolGains.map((stabilityPoolGain: AssetBalance) => {
    const price = get(assetPrice(stabilityPoolGain.asset)) ?? One;

    return {
      ...stabilityPoolGain,
      usdValue: stabilityPoolGain.amount.multipliedBy(price),
    };
  });

  const totalUsdGainsStabilityPool = bigNumberSum(stabilityPoolGains.map(({ usdValue }) => usdValue));

  const totalUsdGainsStaking = bigNumberSum(stakingGains.map(({ usdValue }) => usdValue));

  return {
    ...statisticVal,
    stabilityPoolGains,
    stakingGains,
    totalDepositedStabilityPoolUsdValue: statisticVal.totalDepositedStabilityPool.multipliedBy(get(lusdPrice) ?? One),
    totalUsdGainsStabilityPool,
    totalUsdGainsStaking,
    totalWithdrawnStabilityPoolUsdValue: statisticVal.totalWithdrawnStabilityPool.multipliedBy(get(lusdPrice) ?? One),
  };
});

const totalDepositedStabilityPoolBalance = useRefMap<LiquityStatisticDetails | null, Balance | null>(
  statisticWithAdjustedPrice,
  (data) => {
    if (!data)
      return null;

    return {
      amount: data.totalDepositedStabilityPool,
      usdValue: data.totalDepositedStabilityPoolUsdValue,
    };
  },
);

const totalWithdrawnStabilityPoolBalance = useRefMap<LiquityStatisticDetails | null, Balance | null>(
  statisticWithAdjustedPrice,
  (data) => {
    if (!data)
      return null;

    return {
      amount: data.totalWithdrawnStabilityPool,
      usdValue: data.totalWithdrawnStabilityPoolUsdValue,
    };
  },
);

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
function calculatePnl(
  totalDepositedStabilityPool: BigNumber,
  totalWithdrawnStabilityPool: BigNumber,
  totalUsdGainsStabilityPool: BigNumber,
  poolGains: AssetBalance,
  poolRewards: AssetBalance,
  poolDeposited: AssetBalance,
): ComputedRef<BigNumber> {
  return computed(() => {
    const expectedAmount = totalDepositedStabilityPool.minus(totalWithdrawnStabilityPool);

    const liquidationGainsInCurrentPrice = poolGains.amount.multipliedBy(get(assetPrice(poolGains.asset)) ?? One);

    const rewardsInCurrentPrice = poolRewards.amount.multipliedBy(get(assetPrice(poolRewards.asset)) ?? One);

    const totalWithdrawals = totalUsdGainsStabilityPool
      .plus(liquidationGainsInCurrentPrice)
      .plus(rewardsInCurrentPrice);

    const diffDeposited = expectedAmount.minus(poolDeposited.amount);

    const diffDepositedInCurrentUsdPrice = diffDeposited.multipliedBy(get(lusdPrice) ?? One);

    return totalWithdrawals.minus(diffDepositedInCurrentUsdPrice);
  });
}

const totalPnl = computed<BigNumber | null>(() => {
  const statisticVal = get(statistic);
  const poolVal = get(pool);

  if (!statisticVal || !poolVal)
    return null;

  return get(
    calculatePnl(
      statisticVal.totalDepositedStabilityPool,
      statisticVal.totalWithdrawnStabilityPool,
      statisticVal.totalUsdGainsStabilityPool,
      poolVal.gains,
      poolVal.rewards,
      poolVal.deposited,
    ),
  );
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
          v-model="selection"
          required
          variant="outlined"
          color="primary"
        >
          <RuiButton model-value="current">
            {{ t('liquity_statistic.switch.current') }}
          </RuiButton>
          <RuiButton model-value="historical">
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
          <AmountDisplay
            :value="statisticWithAdjustedPrice.totalUsdGainsStabilityPool"
            :fiat-currency="CURRENCY_USD"
            class="font-bold"
            :loading="loading"
          />
        </div>
        <div class="flex justify-between">
          <div class="text-rui-text-secondary">
            {{ t('liquity_statistic.total_gains_staking') }}
          </div>
          <AmountDisplay
            :value="statisticWithAdjustedPrice.totalUsdGainsStaking"
            :fiat-currency="CURRENCY_USD"
            class="font-bold"
            :loading="loading"
          />
        </div>
      </div>

      <RuiAccordions class="pt-4">
        <RuiAccordion
          header-class="pt-4 pb-4 -mb-4 border-t border-default justify-center w-full"
          class="flex-col-reverse"
        >
          <div class="grid md:grid-cols-2 md:gap-12">
            <div>
              <div>
                <RuiDivider />
                <div class="text-right py-4">
                  <div class="font-medium pb-2">
                    {{ t('liquity_statistic.total_deposited_stability_pool') }}
                  </div>
                  <BalanceDisplay
                    :asset="LUSD_ID"
                    :value="totalDepositedStabilityPoolBalance"
                    :loading="loading"
                  />
                </div>
              </div>
              <div>
                <RuiDivider />
                <div class="text-right py-4">
                  <div class="font-medium pb-2">
                    {{ t('liquity_statistic.total_withdrawn_stability_pool') }}
                  </div>
                  <BalanceDisplay
                    :asset="LUSD_ID"
                    :value="totalWithdrawnStabilityPoolBalance"
                    :loading="loading"
                  />
                </div>
              </div>
              <div>
                <RuiDivider />
                <div class="text-right py-4">
                  <div class="font-medium pb-2">
                    {{ t('liquity_statistic.stability_pool_gains') }}
                  </div>

                  <div v-if="statisticWithAdjustedPrice.stabilityPoolGains.length > 0">
                    <div
                      v-for="assetBalance in statisticWithAdjustedPrice.stabilityPoolGains"
                      :key="assetBalance.asset"
                    >
                      <BalanceDisplay
                        :asset="assetBalance.asset"
                        :value="assetBalance"
                        :loading="loading"
                      />
                    </div>
                  </div>
                  <div
                    v-else
                    class="text-rui-text-secondary pb-2"
                  >
                    {{ t('liquity_statistic.no_stability_pool_gains') }}
                  </div>
                </div>
              </div>
              <div v-if="totalPnl">
                <RuiDivider />
                <div class="text-right py-4">
                  <div class="flex items-center justify-end gap-2 font-medium pb-2">
                    <RuiTooltip
                      :popper="{ placement: 'top' }"
                      :open-delay="400"
                      tooltip-class="max-w-[10rem]"
                    >
                      <template #activator>
                        <RuiIcon name="lu-info" />
                      </template>
                      <span>
                        {{ t('liquity_statistic.estimated_pnl_warning') }}
                      </span>
                    </RuiTooltip>
                    {{ t('liquity_statistic.estimated_pnl') }}
                  </div>
                  <AmountDisplay
                    :value="totalPnl"
                    :fiat-currency="CURRENCY_USD"
                    :loading="loading"
                    pnl
                  />
                </div>
              </div>
            </div>
            <div>
              <div>
                <RuiDivider />
                <div class="text-right py-4">
                  <div class="font-medium pb-2">
                    {{ t('liquity_statistic.staking_gains') }}
                  </div>

                  <div v-if="statisticWithAdjustedPrice.stakingGains.length > 0">
                    <div
                      v-for="assetBalance in statisticWithAdjustedPrice.stakingGains"
                      :key="assetBalance.asset"
                    >
                      <BalanceDisplay
                        :asset="assetBalance.asset"
                        :value="assetBalance"
                        :loading="loading"
                      />
                    </div>
                  </div>
                  <div
                    v-else
                    class="text-rui-text-secondary pb-2"
                  >
                    {{ t('liquity_statistic.no_staking_gains') }}
                  </div>
                </div>
              </div>
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
    >
      {{ t('liquity_statistic.no_statistics') }}
    </div>
  </RuiCard>
</template>
