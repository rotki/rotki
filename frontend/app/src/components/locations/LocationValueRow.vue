<template>
  <v-row>
    <v-col cols="4">
      <v-card>
        <v-card-title>
          <card-title>{{ t('locations.total_asset_price') }}</card-title>
        </v-card-title>
        <v-card-text class="text-end text-h5 font-weight-medium">
          <amount-display
            class="pt-4"
            tooltip
            show-currency="symbol"
            :fiat-currency="currencySymbol"
            :amount="totalValue"
            :value="totalValue"
          />
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed, toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { useBalancesStore } from '@/store/balances';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Zero } from '@/utils/bignumbers';

const props = defineProps({
  identifier: { required: true, type: String }
});

const { identifier } = toRefs(props);

const { t } = useI18n();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { balancesByLocation } = storeToRefs(useBalancesStore());

const totalValue = computed<BigNumber>(() => {
  const locations = get(balancesByLocation);
  return locations?.[identifier.value] ?? Zero;
});
</script>
