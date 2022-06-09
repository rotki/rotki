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
        {{ $t('asset_icon.tooltip', tooltip) }}
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
import { get, set } from '@vueuse/core';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import GeneratedIcon from '@/components/helper/display/icons/GeneratedIcon.vue';
import { currencies } from '@/data/currencies';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval } from '@/store/assets';

export default defineComponent({
  name: 'AssetIcon',
  components: { AdaptiveWrapper, GeneratedIcon },
  props: {
    identifier: { required: true, type: String },
    symbol: { required: false, type: String, default: '' },
    size: { required: true, type: String },
    changeable: { required: false, type: Boolean, default: false },
    styled: { required: false, type: Object, default: () => null },
    noTooltip: { required: false, type: Boolean, default: false },
    timestamp: { required: false, type: Number, default: null }
  },
  setup(props) {
    const { symbol, changeable, identifier, timestamp } = toRefs(props);
    const error = ref<boolean>(false);

    const { assetSymbol, assetName, assetIdentifierForSymbol } =
      useAssetInfoRetrieval();

    watch([symbol, changeable, identifier], () => set(error, false));

    const currency = computed<string | undefined>(() => {
      const id = get(identifier);
      if ([Blockchain.BTC, Blockchain.ETH].includes(id as Blockchain)) {
        return undefined;
      }
      return currencies.find(({ tickerSymbol }) => tickerSymbol === id)
        ?.unicodeSymbol;
    });

    const displayAsset = computed<string>(() => {
      const id = get(identifier);
      const matchedSymbol = get(assetSymbol(id));
      if (get(error)) {
        return get(symbol) || matchedSymbol;
      }
      return get(currency) || matchedSymbol || id;
    });

    const tooltip = computed(() => {
      const id = get(identifier);
      return {
        symbol: get(assetSymbol(id)),
        name: get(assetName(id))
      };
    });

    const url = computed<string>(() => {
      let id = get(identifier);
      if (
        get(symbol) === 'WETH' ||
        get(assetIdentifierForSymbol('WETH')) === id
      ) {
        return `/assets/images/defi/weth.svg`;
      }
      const url = `${api.serverUrl}/api/1/assets/${id}/icon`;
      const currentTimestamp = get(timestamp) || Date.now();
      return get(changeable) ? `${url}?t=${currentTimestamp}` : url;
    });

    return {
      currency,
      error,
      displayAsset,
      tooltip,
      url,
      assetSymbol,
      assetName
    };
  }
});
</script>
