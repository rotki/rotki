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
      <div class="flex items-center justify-end gap-2">
        <RuiTooltip
          :options="{ placement: 'top' }"
          :open-delay="400"
          :class-names="{ tooltip: 'max-w-[10rem]' }"
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
    </template>
    <FiatDisplay
      :value="value"
      :loading="loading"
      pnl
    />
  </LiquityStatisticRow>
</template>
