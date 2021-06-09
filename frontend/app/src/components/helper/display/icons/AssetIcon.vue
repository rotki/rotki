<template>
  <generated-icon
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
import { Component, Mixins, Prop, Watch } from 'vue-property-decorator';
import GeneratedIcon from '@/components/helper/display/icons/GeneratedIcon.vue';
import { currencies } from '@/data/currencies';
import AssetMixin from '@/mixins/asset-mixin';
import { TokenDetails } from '@/services/defi/types';
import { BTC, ETH } from '@/typing/types';

@Component({
  components: { GeneratedIcon }
})
export default class AssetIcon extends Mixins(AssetMixin) {
  @Prop({ required: true })
  identifier!: TokenDetails;
  @Prop({ required: false, type: String, default: '' })
  symbol!: string;
  @Prop({ required: true, type: String })
  size!: string;
  @Prop({ required: false, type: Boolean, default: false })
  changeable!: boolean;

  error: boolean = false;

  @Watch('symbol')
  onSymbolChange() {
    this.error = false;
  }

  @Watch('changeable')
  onChange() {
    this.error = false;
  }

  @Watch('identifier')
  onIdentifierChange() {
    this.error = false;
  }

  get isUnknown(): boolean {
    return typeof this.identifier !== 'string';
  }

  get asset(): string {
    return this.getIdentifier(this.identifier);
  }

  get displayAsset(): string {
    if (typeof this.identifier !== 'string') {
      return this.identifier.symbol ?? '';
    }

    const symbol = this.symbol;
    if (this.error && symbol) {
      return symbol;
    }
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
    if (
      this.symbol === 'WETH' ||
      this.getIdentifierForSymbol('WETH') === this.identifier
    ) {
      return require(`@/assets/images/defi/weth.svg`);
    }
    const url = `${process.env.VUE_APP_BACKEND_URL}/api/1/assets/${this.asset}/icon`;
    return this.changeable ? `${url}?t=${Date.now()}` : url;
  }
}
</script>
