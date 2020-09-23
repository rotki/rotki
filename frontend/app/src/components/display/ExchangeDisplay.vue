<template>
  <div class="d-flex flex-row align-center shrink">
    <v-img
      width="24px"
      height="24px"
      contain
      class="exchange-display__icon"
      :src="require(`@/assets/images/${exchange}.png`)"
    />
    <div class="ml-2">{{ exchange | capitalize }}</div>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { SupportedExchange } from '@/services/balances/types';

@Component({})
export default class ExchangeDisplay extends Vue {
  @Prop({ required: true })
  exchange!: SupportedExchange;
}
</script>

<style scoped lang="scss">
.exchange-display {
  &__icon {
    filter: grayscale(100%);
  }
}
</style>
