<template>
  <v-row class="mt-8" no-gutters>
    <v-col cols="12">
      <stat-card-wide :cols="3">
        <template #first-col>
          <stat-card-column>
            <template #title>
              {{ t('lending.currently_deposited') }}
            </template>
            <amount-display
              :value="totalLendingDeposit"
              fiat-currency="USD"
              show-currency="symbol"
            />
          </stat-card-column>
        </template>
        <template #second-col>
          <stat-card-column>
            <template #title>
              {{ t('lending.effective_interest_rate') }}
              <v-tooltip bottom max-width="300px">
                <template #activator="{ on }">
                  <v-icon small class="mb-3 ml-1" v-on="on">
                    mdi-information
                  </v-icon>
                </template>
                <div>{{ t('lending.effective_interest_rate_tooltip') }}</div>
              </v-tooltip>
            </template>
            <percentage-display
              justify="start"
              :value="effectiveInterestRate"
            />
          </stat-card-column>
        </template>
        <template #third-col>
          <stat-card-column lock>
            <template #title>
              {{ t('lending.profit_earned') }}
              <premium-lock v-if="!premium" class="d-inline" />
            </template>
            <amount-display
              v-if="premium"
              :loading="loading"
              :value="totalUsdEarned"
              show-currency="symbol"
              fiat-currency="USD"
            />
          </stat-card-column>
        </template>
      </stat-card-wide>
    </v-col>
  </v-row>
</template>
<script setup lang="ts">
import { BigNumber } from '@rotki/common';

import StatCardColumn from '@/components/display/StatCardColumn.vue';
import StatCardWide from '@/components/display/StatCardWide.vue';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { usePremium } from '@/composables/premium';

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
