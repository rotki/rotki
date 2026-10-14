<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useSetting } from '@/modules/settings/use-setting';

/**
 * What the staking has earned, as two figures read first: its value when each reward arrived, and
 * what the same rewards are worth now.
 */
defineProps<{
  /** Whether a current price is still missing for some earned asset. */
  loading: boolean;
  totalHistorical: BigNumber;
  totalCurrent: BigNumber;
  /** How many staking rewards the figures add up, which says how much history they cover. */
  rewardsCount: number;
}>();

const { t } = useI18n({ useScope: 'global' });
const currencySymbol = useSetting('currencySymbol');

/** Outside USD the historical values are converted at today's rate, which the one hint also says. */
const convertedFromUsd = computed<boolean>(() => get(currencySymbol) !== CURRENCY_USD);
</script>

<template>
  <RuiCard class="h-auto">
    <template #header>
      {{ t('kraken_staking_overview.title') }}
    </template>
    <div class="grid sm:grid-cols-2 gap-4">
      <div>
        <div class="flex items-center gap-1.5 text-sm text-rui-text-secondary">
          {{ t('kraken_staking_overview.historical') }}
          <RuiTooltip
            :options="{ placement: 'top' }"
            :open-delay="400"
            :class-names="{ tooltip: 'max-w-64' }"
          >
            <template #activator>
              <RuiIcon
                size="16"
                name="lu-info"
              />
            </template>
            <span>{{ t('kraken_staking_overview.hint.historical') }}</span>
            <span
              v-if="convertedFromUsd"
              class="block mt-1"
            >
              {{ t('price_accuracy_hint.tooltip') }}
            </span>
          </RuiTooltip>
        </div>
        <FiatDisplay
          :value="totalHistorical"
          class="text-h5 font-semibold"
          data-testid="kraken-total-historical"
        />
      </div>
      <div>
        <div class="flex items-center gap-1.5 text-sm text-rui-text-secondary">
          {{ t('kraken_staking_overview.current') }}
          <RuiTooltip
            :options="{ placement: 'top' }"
            :open-delay="400"
            :class-names="{ tooltip: 'max-w-64' }"
          >
            <template #activator>
              <RuiIcon
                size="16"
                name="lu-info"
              />
            </template>
            <span>{{ t('kraken_staking_overview.hint.current') }}</span>
          </RuiTooltip>
        </div>
        <FiatDisplay
          :value="totalCurrent"
          :loading="loading"
          class="text-h5 font-semibold"
          data-testid="kraken-total-current"
        />
      </div>
    </div>
    <div
      class="mt-4 text-sm text-rui-text-secondary"
      data-testid="kraken-rewards-count"
    >
      {{ t('kraken_staking_overview.rewards_count', { count: rewardsCount }, rewardsCount) }}
    </div>
  </RuiCard>
</template>
