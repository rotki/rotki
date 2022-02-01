<template>
  <adaptive-wrapper>
    <v-tooltip top open-delay="400" :disabled="noTooltip">
      <template #activator="{ on, attrs }">
        <div v-bind="attrs" :style="styled" class="d-flex" v-on="on">
          <generated-icon
            v-if="!!currency || error"
            :asset="displayAsset"
            :currency="!!currency"
            :size="size"
          />
          <v-img
            v-else-if="!error"
            :src="url"
            :max-height="size"
            :min-height="size"
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
            symbol: getAssetSymbol(identifier),
            name: getAssetName(identifier)
          })
        }}
      </span>
    </v-tooltip>
  </adaptive-wrapper>
</template>

<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import GeneratedIcon from '@/components/helper/display/icons/GeneratedIcon.vue';
import { setupAssetInfoRetrieval } from '@/composables/balances';
import { currencies } from '@/data/currencies';
import { api } from '@/services/rotkehlchen-api';

export default defineComponent({
  name: 'AssetIcon',
  components: { AdaptiveWrapper, GeneratedIcon },
  props: {
    identifier: { required: true, type: String },
    symbol: { required: false, type: String, default: '' },
    size: { required: true, type: String },
    changeable: { required: false, type: Boolean, default: false },
    styled: { required: false, type: Object, default: () => null },
    noTooltip: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { symbol, changeable, identifier } = toRefs(props);
    const error = ref<boolean>(false);

    const { getAssetSymbol, getAssetName, getAssetIdentifierForSymbol } =
      setupAssetInfoRetrieval();

    watch([symbol, changeable, identifier], () => {
      error.value = false;
    });

    const currency = computed<string | undefined>(() => {
      if (
        [Blockchain.BTC, Blockchain.ETH].includes(
          identifier.value as Blockchain
        )
      ) {
        return undefined;
      }
      return currencies.find(
        ({ tickerSymbol }) => tickerSymbol === identifier.value
      )?.unicodeSymbol;
    });

    const displayAsset = computed<string>(() => {
      if (error.value && symbol.value) {
        return symbol.value;
      }
      return currency.value || identifier.value;
    });

    const url = computed<string>(() => {
      if (
        symbol.value === 'WETH' ||
        getAssetIdentifierForSymbol('WETH') === identifier.value
      ) {
        return require(`@/assets/images/defi/weth.svg`);
      }
      const url = `${api.serverUrl}/api/1/assets/${identifier.value}/icon`;
      return changeable.value ? `${url}?t=${Date.now()}` : url;
    });

    return {
      currency,
      error,
      displayAsset,
      url,
      getAssetSymbol,
      getAssetName
    };
  }
});
</script>
