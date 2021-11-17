<template>
  <v-tooltip top open-delay="400">
    <template #activator="{ on, attrs }">
      <div v-bind="attrs" :style="styled" v-on="on">
        <generated-icon
          v-if="!!currency || error"
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
      </div>
    </template>
    <span>
      {{
        $t('asset_icon.tooltip', {
          symbol: getSymbol(identifier),
          name: getAssetName(identifier)
        })
      }}
    </span>
  </v-tooltip>
</template>

<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Component, Mixins, Prop, Watch } from 'vue-property-decorator';
import GeneratedIcon from '@/components/helper/display/icons/GeneratedIcon.vue';
import { currencies } from '@/data/currencies';
import AssetMixin from '@/mixins/asset-mixin';

@Component({
  components: { GeneratedIcon }
})
export default class AssetIcon extends Mixins(AssetMixin) {
  @Prop({ required: true })
  identifier!: string;
  @Prop({ required: false, type: String, default: '' })
  symbol!: string;
  @Prop({ required: true, type: String })
  size!: string;
  @Prop({ required: false, type: Boolean, default: false })
  changeable!: boolean;
  @Prop({ required: false, type: Object, default: () => null })
  styled!: any;

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

  get asset(): string {
    return this.identifier;
  }

  get displayAsset(): string {
    const symbol = this.symbol ? this.symbol : this.getSymbol(this.identifier);
    if (this.error && symbol) {
      return symbol;
    }
    return this.currency || this.asset;
  }

  get currency(): string | undefined {
    if (this.asset === Blockchain.BTC || this.asset === Blockchain.ETH) {
      return undefined;
    }
    return currencies.find(({ tickerSymbol }) => tickerSymbol === this.asset)
      ?.unicodeSymbol;
  }

  get url(): string {
    if (
      this.symbol === 'WETH' ||
      this.getIdentifierForSymbol('WETH') === this.identifier
    ) {
      return require(`@/assets/images/defi/weth.svg`);
    }
    const url = `${this.$api.serverUrl}/api/1/assets/${this.asset}/icon`;
    return this.changeable ? `${url}?t=${Date.now()}` : url;
  }
}
</script>
