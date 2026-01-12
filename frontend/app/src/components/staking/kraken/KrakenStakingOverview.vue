<script setup lang="ts">
import type { AssetBalance, BigNumber } from '@rotki/common';
import ValueAccuracyHint from '@/components/helper/hint/ValueAccuracyHint.vue';
import { FiatDisplay } from '@/modules/amount-display/components';
import { sum } from '@/utils/balances';

const props = defineProps<{
  loading: boolean;
  totalHistorical: BigNumber;
  earned: AssetBalance[];
}>();

const { earned } = toRefs(props);

const totalCurrent = computed<BigNumber>(() => {
  const earnedAssets = get(earned);
  return sum(earnedAssets);
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('kraken_staking_overview.title') }}
    </template>
    <div class="font-medium">
      {{ t('kraken_staking_overview.earned') }}
    </div>
    <div class="mt-2 ml-4 flex flex-col gap-2">
      <div class="flex justify-between items-center">
        <div class="flex items-center text-rui-text-secondary gap-2 font-light">
          {{ t('kraken_staking_overview.historical') }}
          <RuiTooltip
            :popper="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiIcon
                size="20"
                name="lu-info"
              />
            </template>
            <span>{{ t('kraken_staking_overview.hint.historical') }}</span>
          </RuiTooltip>
        </div>
        <div class="flex items-center">
          <ValueAccuracyHint />
          <FiatDisplay
            :value="totalHistorical"
            symbol="ticker"
            class="text-rui-text-secondary"
          />
        </div>
      </div>
      <div class="flex justify-between items-center">
        <div class="flex items-center text-rui-text-secondary gap-2 font-light">
          {{ t('kraken_staking_overview.current') }}
          <RuiTooltip
            :popper="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiIcon
                size="20"
                name="lu-info"
              />
            </template>
            <span>{{ t('kraken_staking_overview.hint.current') }}</span>
          </RuiTooltip>
        </div>
        <FiatDisplay
          :value="totalCurrent"
          :loading="loading"
          symbol="ticker"
          class="text-rui-text-secondary"
        />
      </div>
    </div>
  </RuiCard>
</template>
