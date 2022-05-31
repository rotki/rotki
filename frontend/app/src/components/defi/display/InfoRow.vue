<template>
  <div class="d-flex justify-space-between">
    <div>
      {{ title }}
    </div>
    <slot>
      <amount-display
        :fiat-currency="fiat ? 'USD' : null"
        :value="value"
        :loading="loading"
        :show-currency="fiat ? 'none' : 'ticker'"
      />
    </slot>
  </div>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { defineComponent } from '@vue/composition-api';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { Zero } from '@/utils/bignumbers';

export default defineComponent({
  name: 'InfoRow',

  components: { AmountDisplay },
  props: {
    loading: { required: false, type: Boolean },
    title: { required: true, type: String },
    value: {
      required: false,
      type: BigNumber,
      default: () => Zero
    },
    fiat: { required: false, type: Boolean }
  }
});
</script>
