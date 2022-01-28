<template>
  <card :class="$style.full">
    <template #title>{{ $t('kraken_staking_overview.title') }}</template>
    <v-row justify="space-between" class="text-h6 py-4" align="center">
      <v-col cols="auto" class="font-weight-medium">
        {{ $t('kraken_staking_overview.total') }}
      </v-col>
      <v-col cols="auto">
        <amount-display
          show-currency="ticker"
          fiat-currency="USD"
          :value="totalUsd"
        />
      </v-col>
    </v-row>
  </card>
</template>
<script lang="ts">
import { BigNumber } from '@rotki/common';
import { defineComponent, PropType } from '@vue/composition-api';

export default defineComponent({
  name: 'KrakenStakingOverview',
  props: {
    totalUsd: { required: true, type: Object as PropType<BigNumber> }
  }
});
</script>

<style lang="scss" module>
.full {
  height: 100%;
}
</style>
