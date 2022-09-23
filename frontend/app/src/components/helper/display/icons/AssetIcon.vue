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
import { api } from '@/services/rotkehlchen-api';
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
  name: { required: false, type: String, default: null },
  size: { required: true, type: String },
  changeable: { required: false, type: Boolean, default: false },
  styled: { required: false, type: Object, default: () => null },
  noTooltip: { required: false, type: Boolean, default: false },
  timestamp: { required: false, type: Number, default: null },
  circle: { required: false, type: Boolean, default: false },
  padding: { required: false, type: String, default: '2px' }
});
const { symbol, name, changeable, identifier, timestamp, padding, size } =
  toRefs(props);
const error = ref<boolean>(false);

const { t } = useI18n();
const css = useCssModule();

const currency = computed<string | undefined>(() => {
  const id = get(identifier);
  if ([Blockchain.BTC, Blockchain.ETH].includes(id as Blockchain)) {
    return undefined;
  }
  return currencies.find(({ tickerSymbol }) => tickerSymbol === id)
    ?.unicodeSymbol;
});

const displayAsset = computed<string>(() => {
  if (get(error)) {
    return get(symbol);
  }
  return get(currency) || get(identifier);
});

const tooltip = computed(() => {
  return {
    symbol: get(symbol),
    name: get(name)
  };
});

const url = computed<string>(() => {
  let id = get(identifier);
  if (get(symbol) === 'WETH') {
    return `/assets/images/defi/weth.svg`;
  }
  const currentTimestamp = get(timestamp) || Date.now();

  return api.assets.assetImageUrl(
    id,
    get(changeable) ? currentTimestamp : undefined
  );
});

const placeholderStyle = computed(() => {
  let pad = get(padding);
  let width = get(size);
  let prop = `calc(${pad} + ${pad} + ${width})`;
  return {
    'min-width': prop,
    height: prop
  };
});

watch([symbol, changeable, identifier], () => set(error, false));
</script>
<style module lang="scss">
.circle {
  border-radius: 50%;
  overflow: hidden;
}
</style>
