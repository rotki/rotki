<template>
  <genereted-icon
    v-if="!!currency || error || isUnknown"
    :asset="displayAsset"
    :currency="!!currency"
    :size="size"
  />
  <v-img
    v-else-if="!error"
    :src="url"
    :max-width="size"
    :min-width="size"
    contain
    @error="error = true"
  />
</template>

<script lang="ts">
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import GeneretedIcon from '@/components/helper/GeneretedIcon.vue';
import { currencies } from '@/data/currencies';
import { TokenDetails } from '@/services/defi/types';
import { assetName } from '@/store/defi/utils';
import { BTC, ETH } from '@/typing/types';

@Component({
  components: { GeneretedIcon }
})
export default class CryptoIcon extends Vue {
  @Prop({ required: true })
  symbol!: TokenDetails;
  @Prop({ required: true, type: String })
  size!: string;
  error: boolean = false;

  @Watch('symbol')
  onSymbolChange() {
    this.error = false;
  }

  get isUnknown(): boolean {
    return typeof this.symbol !== 'string';
  }

  get asset(): string {
    return assetName(this.symbol);
  }

  get displayAsset(): string {
    return this.currency || this.asset;
  }

  get currency(): string | undefined {
    if (this.asset === BTC || this.asset === ETH) {
      return undefined;
    }
    return currencies.find(({ ticker_symbol }) => ticker_symbol === this.asset)
      ?.unicode_symbol;
  }

  get url(): string {
    if (this.asset === 'WETH') {
      return require(`@/assets/images/defi/weth.svg`);
    }
    return `${process.env.VUE_APP_BACKEND_URL}/api/1/assets/${this.asset}/icon/small`;
  }
}
</script>
