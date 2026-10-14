<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import LiquityStatisticRow from '@/modules/staking/liquity/LiquityStatisticRow.vue';

const { loading, value } = defineProps<{
  value: BigNumber;
  loading?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <LiquityStatisticRow>
    <template #label>
      <div class="flex items-center gap-1.5">
        {{ t('liquity_statistic.estimated_pnl') }}
        <RuiTooltip
          :options="{ placement: 'top' }"
          :open-delay="400"
          :class-names="{ tooltip: 'max-w-40' }"
        >
          <template #activator>
            <RuiIcon
              name="lu-info"
              size="16"
            />
          </template>
          <span>
            {{ t('liquity_statistic.estimated_pnl_warning') }}
          </span>
        </RuiTooltip>
      </div>
    </template>
    <FiatDisplay
      :value="value"
      :loading="loading"
      class="py-1 pr-10 font-medium"
      pnl
    />
  </LiquityStatisticRow>
</template>
