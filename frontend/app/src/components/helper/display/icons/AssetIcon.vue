<template>
  <div :style="placeholderStyle">
    <adaptive-wrapper :circle="circle" :padding="padding">
      <v-tooltip top open-delay="400" :disabled="noTooltip">
        <template #activator="{ on, attrs }">
          <div
            v-if="chainIcon"
            :class="{
              [css.circle]: true,
              [css.chain]: true
            }"
          >
            <v-img
              :src="chainIcon"
              :width="chainIconSize"
              :height="chainIconSize"
              contain
            />
          </div>

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
import { EvmChain } from '@rotki/common/lib/data';
import { PropType } from 'vue';
import { api } from '@/services/rotkehlchen-api';
import { getChainIcon } from '@/types/blockchain/chains';
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
  chain: {
    required: false,
    type: String as PropType<EvmChain | null>,
    default: null
  },
  changeable: { required: false, type: Boolean, default: false },
  styled: { required: false, type: Object, default: () => null },
  noTooltip: { required: false, type: Boolean, default: false },
  timestamp: { required: false, type: Number, default: null },
  circle: { required: false, type: Boolean, default: false },
  padding: { required: false, type: String, default: '2px' }
});
const {
  symbol,
  name,
  chain,
  changeable,
  identifier,
  timestamp,
  padding,
  size
} = toRefs(props);
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

const chainIconSize = computed(() => `${(parseInt(get(size)) * 33) / 100}px`);
const chainWrapperSize = computed(
  () => `${parseInt(get(chainIconSize)) + 3}px`
);
const chainIconMargin = computed(() => `-${get(chainIconSize)}`);
const chainIconTop = computed(() => {
  return `${(parseInt(get(chainIconSize)) * 80) / 100}px`;
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

const chainIcon = computed(() => getChainIcon(get(chain)));

watch([symbol, changeable, identifier], () => set(error, false));
</script>
<style module lang="scss">
.circle {
  border-radius: 50%;
  overflow: hidden;
}

.chain {
  border: 1px solid rgb(200, 200, 200);
  background-color: white;
  position: relative;
  margin-top: v-bind(chainIconMargin);
  top: v-bind(chainIconTop);
  width: v-bind(chainWrapperSize);
  height: v-bind(chainWrapperSize);
  z-index: 8;
}
</style>
