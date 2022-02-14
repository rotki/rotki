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
import { setupGeneralSettings } from '@/composables/session';
import { useStore } from '@/store/utils';
import { Zero } from '@/utils/bignumbers';

export default defineComponent({
  name: 'LocationValueRow',
  props: {
    identifier: { required: true, type: String }
  },
  setup(props) {
    const { identifier } = toRefs(props);

    const { currencySymbol } = setupGeneralSettings();

    const store = useStore();
    const totalValue = computed<BigNumber>(() => {
      const locations = store.getters['balances/byLocation'];
      return locations?.[identifier.value] ?? Zero;
    });

    return {
      currencySymbol,
      totalValue
    };
  }
});
</script>
