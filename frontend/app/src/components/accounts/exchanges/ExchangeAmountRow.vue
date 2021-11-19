<template>
  <div class="d-flex flex-row">
    <div class="ml-2 mr-6">
      <location-display :identifier="exchange" size="48px" icon />
    </div>
    <div class="d-flex flex-column my-3">
      <span class="text-h6">
        {{ exchangeName(exchange) }}
      </span>
      <span class="secondary--text text--lighten-5">
        <amount-display
          show-currency="symbol"
          fiat-currency="USD"
          :value="balance"
        />
      </span>
    </div>
  </div>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { exchangeName } from '@/components/history/consts';
import { SupportedExchange } from '@/types/exchanges';

@Component({
  name: 'ExchangeAmountRow'
})
export default class ExchangeAmountRow extends Vue {
  readonly exchangeName = exchangeName;
  @Prop({ required: true })
  balance!: BigNumber;
  @Prop({ required: true, type: String })
  exchange!: SupportedExchange;
}
</script>
