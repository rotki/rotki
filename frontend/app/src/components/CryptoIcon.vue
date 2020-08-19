<template>
  <genereted-icon
    v-if="!!currency || error"
    :asset="displayAsset"
    :currency="!!currency"
    :size="size"
  />
  <v-img
    v-else-if="!error"
    :src="url"
    :max-width="size"
    contain
    @error="error = true"
  />
</template>

<script lang="ts">
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import GeneretedIcon from '@/components/helper/GeneretedIcon.vue';
import { currencies } from '@/data/currencies';

@Component({
  components: { GeneretedIcon }
})
export default class CryptoIcon extends Vue {
  @Prop({ required: true })
  symbol!: string;
  @Prop({ required: true, type: String })
  size!: string;
  error: boolean = false;

  @Watch('symbol')
  onSymbolChange() {
    this.error = false;
  }

  get displayAsset(): string {
    return this.currency || this.symbol;
  }

  get currency(): string | undefined {
    return currencies.find(currency => currency.ticker_symbol === this.symbol)
      ?.unicode_symbol;
  }

  get url(): string {
    return `${process.env.VUE_APP_BACKEND_URL}/api/1/assets/${this.symbol}/icon/small`;
  }
}
</script>
