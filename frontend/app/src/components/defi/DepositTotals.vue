<script setup lang="ts">
import { BigNumber } from '@rotki/common';

defineProps({
  loading: {
    required: true,
    type: Boolean
  },
  totalUsdEarned: {
    required: true,
    type: BigNumber
  },
  effectiveInterestRate: {
    required: true,
    type: String
  },
  totalLendingDeposit: {
    required: true,
    type: BigNumber
  }
});
const premium = usePremium();

const { t } = useI18n();
</script>

<template>
  <VRow class="mt-8" no-gutters>
    <VCol cols="12">
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
              <VTooltip bottom max-width="300px">
                <template #activator="{ on }">
                  <VIcon small class="mb-1 ml-2" v-on="on">
                    mdi-information
                  </VIcon>
                </template>
                <div>{{ t('lending.effective_interest_rate_tooltip') }}</div>
              </VTooltip>
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
    </VCol>
  </VRow>
</template>
