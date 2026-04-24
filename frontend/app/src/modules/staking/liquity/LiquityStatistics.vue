<script setup lang="ts">
import { type AssetBalance, type Balance, type BigNumber, type LiquityPoolDetailEntry, type LiquityStatisticDetails, One, Zero } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { bigNumberSum } from '@/modules/core/common/data/calculation';
import { Section } from '@/modules/core/common/status';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import { useSectionStatus } from '@/modules/shell/sync-progress/use-section-status';

const { pool = null, statistic = null } = defineProps<{
  statistic?: LiquityStatisticDetails | null;
  pool?: LiquityPoolDetailEntry | null;
}>();

const selection = ref<'historical' | 'current'>('historical');

const { t } = useI18n({ useScope: 'global' });
const { getAssetPrice, useAssetPrice } = usePriceUtils();
const LUSD_ID = 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0';
const lusdPrice = useAssetPrice(LUSD_ID);

function priceOrOne(asset: string): BigNumber {
  const price = getAssetPrice(asset);
  return price && price.gt(0) ? price : One;
}

const lusdPriceOrOne = computed<BigNumber>(() => {
  const price = get(lusdPrice);
  return price && price.gt(0) ? price : One;
});

const { isLoading: loading } = useSectionStatus(Section.DEFI_LIQUITY_STATISTICS);

const statisticWithAdjustedPrice = computed<LiquityStatisticDetails | null>(() => {
  if (!statistic)
    return null;

  if (get(selection) === 'historical')
    return statistic;

  const stakingGains = statistic.stakingGains.map((stakingGain: AssetBalance) => {
    const price = getAssetPrice(stakingGain.asset, One);

    return {
      ...stakingGain,
      value: price.gt(0) ? stakingGain.amount.multipliedBy(price) : Zero,
    };
  });

  const stabilityPoolGains = statistic.stabilityPoolGains.map((stabilityPoolGain: AssetBalance) => {
    const price = getAssetPrice(stabilityPoolGain.asset, One);

    return {
      ...stabilityPoolGain,
      value: price.gt(0) ? stabilityPoolGain.amount.multipliedBy(price) : Zero,
    };
  });

  const totalValueGainsStabilityPool = bigNumberSum(stabilityPoolGains.map(({ value }) => value));

  const totalValueGainsStaking = bigNumberSum(stakingGains.map(({ value }) => value));

  return {
    ...statistic,
    stabilityPoolGains,
    stakingGains,
    totalDepositedStabilityPoolValue: statistic.totalDepositedStabilityPool.multipliedBy(get(lusdPriceOrOne)),
    totalValueGainsStabilityPool,
    totalValueGainsStaking,
    totalWithdrawnStabilityPoolValue: statistic.totalWithdrawnStabilityPool.multipliedBy(get(lusdPriceOrOne)),
  };
});

const totalDepositedStabilityPoolBalance = computed<Balance | null>(() => {
  const data = get(statisticWithAdjustedPrice);
  if (!data)
    return null;

  return {
    amount: data.totalDepositedStabilityPool,
    value: data.totalDepositedStabilityPoolValue,
  };
});

const totalWithdrawnStabilityPoolBalance = computed<Balance | null>(() => {
  const data = get(statisticWithAdjustedPrice);
  if (!data)
    return null;

  return {
    amount: data.totalWithdrawnStabilityPool,
    value: data.totalWithdrawnStabilityPoolValue,
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
 * @param totalValueGainsStabilityPool
 * @param poolGains
 * @param poolRewards
 * @param poolDeposited
 * @return BigNumber
 */
function calculatePnl(
  totalDepositedStabilityPool: BigNumber,
  totalWithdrawnStabilityPool: BigNumber,
  totalValueGainsStabilityPool: BigNumber,
  poolGains: AssetBalance,
  poolRewards: AssetBalance,
  poolDeposited: AssetBalance,
): ComputedRef<BigNumber> {
  return computed(() => {
    const expectedAmount = totalDepositedStabilityPool.minus(totalWithdrawnStabilityPool);

    const liquidationGainsInCurrentPrice = poolGains.amount.multipliedBy(priceOrOne(poolGains.asset));

    const rewardsInCurrentPrice = poolRewards.amount.multipliedBy(priceOrOne(poolRewards.asset));

    const totalWithdrawals = totalValueGainsStabilityPool
      .plus(liquidationGainsInCurrentPrice)
      .plus(rewardsInCurrentPrice);

    const diffDeposited = expectedAmount.minus(poolDeposited.amount);

    const diffDepositedInCurrentUsdPrice = diffDeposited.multipliedBy(get(lusdPriceOrOne));

    return totalWithdrawals.minus(diffDepositedInCurrentUsdPrice);
  });
}

const totalPnl = computed<BigNumber | null>(() => {
  if (!statistic || !pool)
    return null;

  return get(
    calculatePnl(
      statistic.totalDepositedStabilityPool,
      statistic.totalWithdrawnStabilityPool,
      statistic.totalValueGainsStabilityPool,
      pool.gains,
      pool.rewards,
      pool.deposited,
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
          <FiatDisplay
            :value="statisticWithAdjustedPrice.totalValueGainsStabilityPool"
            :loading="loading"
            class="font-bold"
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
                  <FiatDisplay
                    :value="totalPnl"
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
