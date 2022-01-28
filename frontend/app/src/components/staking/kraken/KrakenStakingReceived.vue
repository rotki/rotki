<template>
  <card>
    <template #title>{{ $t('kraken_staking_received.title') }}</template>
    <div :class="$style.received">
      <v-row
        v-for="item in received"
        :key="item.asset"
        justify="space-between"
        no-gutters
        align="center"
      >
        <v-col cols="auto">
          <asset-details :asset="item.asset" />
        </v-col>
        <v-col cols="auto" class="text-h6">
          <amount-display :value="item.amount" />
        </v-col>
      </v-row>
    </div>
  </card>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { ReceivedAmount } from '@/types/staking';

export default defineComponent({
  name: 'KrakenStakingReceived',
  props: {
    received: {
      required: true,
      type: Array as PropType<ReceivedAmount[]>
    }
  }
});
</script>

<style lang="scss" module>
@import '~@/scss/scroll';

.received {
  max-height: 326px;
  overflow-y: scroll;
  overflow-x: hidden;

  @extend .themed-scrollbar;
}
</style>
