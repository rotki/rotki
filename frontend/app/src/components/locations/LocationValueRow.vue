<template>
  <v-row>
    <v-col cols="4">
      <v-card>
        <v-card-title>
          <card-title>{{ $t('locations.total_asset_price') }}</card-title>
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
<script lang="ts">
import { BigNumber } from '@rotki/common';
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useBalancesStore } from '@/store/balances';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Zero } from '@/utils/bignumbers';

export default defineComponent({
  name: 'LocationValueRow',
  props: {
    identifier: { required: true, type: String }
  },
  setup(props) {
    const { identifier } = toRefs(props);

    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
    const { balancesByLocation } = storeToRefs(useBalancesStore());

    const totalValue = computed<BigNumber>(() => {
      const locations = get(balancesByLocation);
      return locations?.[identifier.value] ?? Zero;
    });

    return {
      currencySymbol,
      totalValue
    };
  }
});
</script>
