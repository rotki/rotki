<script setup lang="ts">
import { type AssetBalance } from '@rotki/common';
import { type PropType } from 'vue';

defineProps({
  staking: {
    required: true,
    type: Object as PropType<AssetBalance>
  }
});

const css = useCssModule();
const { tc } = useI18n();
</script>
<template>
  <div :class="css['total-staked-indicator']" class="pl-6">
    <div class="grey--text d-flex align-center py-2">
      {{ tc('transactions.events.extra.total_staked_by_this_tx') }}:
    </div>
    <div class="py-2 d-flex align-center">
      <div class="mr-2">
        <asset-link :asset="staking.asset" icon>
          <asset-icon size="32px" :identifier="staking.asset" />
        </asset-link>
      </div>
      <div>
        <div>
          <amount-display :value="staking.amount" :asset="staking.asset" />
        </div>
        <div>
          <amount-display
            :value="staking.usdValue"
            fiat-currency="USD"
            class="grey--text"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" module>
.total-staked-indicator {
  border-left: 3px solid var(--v-success-base);
}
</style>
