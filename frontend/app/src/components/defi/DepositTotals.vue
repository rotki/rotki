<script setup lang="ts">
import { type BigNumber } from '@rotki/common';

defineProps<{
  loading: boolean;
  totalUsdEarned: BigNumber;
  effectiveInterestRate: BigNumber;
  totalLendingDeposit: BigNumber;
}>();
const premium = usePremium();

const { t } = useI18n();
</script>

<template>
  <StatCardWide :cols="3">
    <template #first-col>
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
    </template>

    <template #second-col>
      <StatCardColumn>
        <template #title>
          {{ t('lending.effective_interest_rate') }}
          <RuiTooltip>
            <template #activator>
              <RuiIcon name="information-line" />
            </template>
            {{ t('lending.effective_interest_rate_tooltip') }}
          </RuiTooltip>
        </template>

        <PercentageDisplay justify="start" :value="effectiveInterestRate" />
      </StatCardColumn>
    </template>

    <template #third-col>
      <StatCardColumn lock>
        <template #title>
          {{ t('lending.profit_earned') }}
          <PremiumLock v-if="!premium" class="d-inline" />
        </template>

        <AmountDisplay
          v-if="premium"
          :loading="loading"
          :value="totalUsdEarned"
          show-currency="symbol"
          fiat-currency="USD"
        />
      </StatCardColumn>
    </template>
  </StatCardWide>
</template>
