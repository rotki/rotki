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
        show-currency="ticker"
      ></amount-display>
    </slot>
  </div>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { Zero } from '@/utils/bignumbers';

@Component({
  components: { AmountDisplay }
})
export default class InfoRow extends Vue {
  @Prop({ required: false, type: Boolean })
  loading!: boolean;

  @Prop({ required: true, type: String })
  title!: string;

  @Prop({ required: false, default: () => Zero })
  value!: BigNumber;

  @Prop({ required: false, type: Boolean })
  fiat!: boolean;
}
</script>

<style scoped></style>
