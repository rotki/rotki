<template>
  <div :style="placeholderStyle">
    <adaptive-wrapper :circle="circle" :padding="padding">
      <v-tooltip top open-delay="400" :disabled="noTooltip">
        <template #activator="{ on, attrs }">
          <div
            v-bind="attrs"
            :style="styled"
            class="d-flex"
            :class="{ [css.circle]: circle }"
            v-on="on"
          >
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
          {{ t('asset_icon.tooltip', tooltip) }}
        </span>
      </v-tooltip>
    </adaptive-wrapper>
  </div>
</template>

<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { get, set } from '@vueuse/core';
import {
  computed,
  defineAsyncComponent,
  ref,
  toRefs,
  useCssModule,
  watch
} from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { currencies } from '@/types/currencies';
const AdaptiveWrapper = defineAsyncComponent(
  () => import('@/components/display/AdaptiveWrapper.vue')
);
const GeneratedIcon = defineAsyncComponent(
  () => import('@/components/helper/display/icons/GeneratedIcon.vue')
);
const props = defineProps({
  identifier: { required: true, type: String },
  symbol: { required: false, type: String, default: '' },
  size: { required: true, type: String },
  changeable: { required: false, type: Boolean, default: false },
  styled: { required: false, type: Object, default: () => null },
  noTooltip: { required: false, type: Boolean, default: false },
  timestamp: { required: false, type: Number, default: null },
  circle: { required: false, type: Boolean, default: false },
  padding: { required: false, type: String, default: '2px' }
});
const { symbol, changeable, identifier, timestamp, padding, size } =
  toRefs(props);
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
  if (get(symbol) === 'WETH' || get(assetIdentifierForSymbol('WETH')) === id) {
    return `/assets/images/defi/weth.svg`;
  }
  const currentTimestamp = get(timestamp) || Date.now();

  return api.assets.assetImageUrl(
    id,
    get(changeable) ? currentTimestamp : undefined
  );
});

const placeholderStyle = computed(() => {
  const placeholderSize = `calc(${get(padding)} + ${get(padding)} + ${get(
    size
  )})`;
  return { minWidth: placeholderSize, height: placeholderSize };
});

const { t } = useI18n();

const css = useCssModule();
</script>
<style module lang="scss">
.circle {
  border-radius: 50%;
  overflow: hidden;
}
</style>
