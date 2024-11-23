<script setup lang="ts">
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import StatCardColumn from '@/components/display/StatCardColumn.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import StatCardWide from '@/components/display/StatCardWide.vue';
import type { BigNumber } from '@rotki/common';

defineProps<{
  loading: boolean;
  totalUsdEarned: BigNumber;
  effectiveInterestRate: BigNumber;
  totalLendingDeposit: BigNumber;
}>();

const { t } = useI18n();
</script>

<template>
  <StatCardWide>
    <StatCardColumn>
      <template #title>
        {{ t('lending.currently_deposited') }}
      </template>

      <AmountDisplay
        :value="totalLendingDeposit"
        fiat-currency="USD"
        show-currency="symbol"
      />
    </StatCardColumn>
    <StatCardColumn>
      <template #title>
        {{ t('lending.effective_interest_rate') }}
        <RuiTooltip tooltip-class="max-w-[10rem]">
          <template #activator>
            <RuiIcon name="lu-info" />
          </template>
          {{ t('lending.effective_interest_rate_tooltip') }}
        </RuiTooltip>
      </template>

      <PercentageDisplay
        justify="start"
        :value="effectiveInterestRate.isNaN() ? undefined : effectiveInterestRate.toString()"
      />
    </StatCardColumn>
    <StatCardColumn premium-only>
      <template #title>
        {{ t('lending.profit_earned') }}
      </template>

      <AmountDisplay
        :loading="loading"
        :value="totalUsdEarned"
        show-currency="symbol"
        fiat-currency="USD"
      />
    </StatCardColumn>
  </StatCardWide>
</template>
