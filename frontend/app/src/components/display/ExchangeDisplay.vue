<template>
  <div class="d-flex flex-row align-center shrink">
    <v-img
      width="24px"
      height="24px"
      contain
      class="exchange-display__icon"
      :src="icon"
    />
    <div class="ml-2" v-text="name" />
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { tradeLocations } from '@/components/history/consts';
import { TradeLocationData } from '@/components/history/type';
import { capitalize } from '@/filters';
import { SupportedExchange } from '@/types/exchanges';

@Component({})
export default class ExchangeDisplay extends Vue {
  @Prop({ required: true })
  exchange!: SupportedExchange;
  readonly locations = tradeLocations;

  get location(): TradeLocationData | undefined {
    return this.locations.find(
      ({ identifier }) => identifier === this.exchange
    );
  }

  get name(): string {
    return this.location?.name ?? capitalize(this.exchange);
  }

  get icon(): string {
    return this.location?.icon ?? '';
  }
}
</script>

<style scoped lang="scss">
.exchange-display {
  &__icon {
    filter: grayscale(100%);
  }
}
</style>
