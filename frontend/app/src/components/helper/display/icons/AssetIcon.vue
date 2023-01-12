<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { getIdentifierFromSymbolMap } from '@rotki/common/lib/data';
import { type ComputedRef } from 'vue';
import TokenPlaceholder from '@/components/svgs/TokenPlaceholder.vue';
import { useAssetIconApi } from '@/services/assets/icon-api';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useCurrencies } from '@/types/currencies';
import EvmChainIcon from '@/components/helper/display/icons/EvmChainIcon.vue';

const AdaptiveWrapper = defineAsyncComponent(
  () => import('@/components/display/AdaptiveWrapper.vue')
);
const GeneratedIcon = defineAsyncComponent(
  () => import('@/components/helper/display/icons/GeneratedIcon.vue')
);

const props = defineProps({
  identifier: { required: true, type: String },
  size: { required: true, type: String },
  changeable: { required: false, type: Boolean, default: false },
  styled: { required: false, type: Object, default: () => null },
  noTooltip: { required: false, type: Boolean, default: false },
  timestamp: { required: false, type: Number, default: null },
  circle: { required: false, type: Boolean, default: false },
  padding: { required: false, type: String, default: '2px' },
  enableAssociation: { required: false, type: Boolean, default: true },
  showChain: { required: false, type: Boolean, default: true }
});
const {
  changeable,
  identifier,
  timestamp,
  padding,
  size,
  enableAssociation,
  showChain
} = toRefs(props);

const error = ref<boolean>(false);
const pending = ref<boolean>(true);

const { t } = useI18n();
const css = useCssModule();

const { currencies } = useCurrencies();

const mappedIdentifier: ComputedRef<string> = computed(() => {
  return getIdentifierFromSymbolMap(get(identifier));
});

const currency = computed<string | undefined>(() => {
  const id = get(mappedIdentifier);
  if ([Blockchain.BTC, Blockchain.ETH].includes(id as Blockchain)) {
    return undefined;
  }

  return get(currencies).find(({ tickerSymbol }) => tickerSymbol === id)
    ?.unicodeSymbol;
});

const { assetInfo } = useAssetInfoRetrieval();
const { assetImageUrl } = useAssetIconApi();

const asset = assetInfo(mappedIdentifier, enableAssociation);
const isCustomAsset = computed(() => get(asset)?.isCustomAsset);
const chain = computed(() => get(asset)?.evmChain);
const symbol = computed(() => get(asset)?.symbol);
const name = computed(() => get(asset)?.name);

const displayAsset = computed<string>(() => {
  const currencySymbol = get(currency);
  if (currencySymbol) return currencySymbol;

  return get(symbol) ?? get(name) ?? get(mappedIdentifier) ?? '';
});

const tooltip = computed(() => {
  if (get(isCustomAsset)) {
    return {
      symbol: get(name),
      name: ''
    };
  }

  return {
    symbol: get(symbol),
    name: get(name)
  };
});

const url = computed<string>(() => {
  const id = get(mappedIdentifier);
  if (get(symbol) === 'WETH') {
    return `./assets/images/defi/weth.svg`;
  }

  const currentTimestamp = get(timestamp) || Date.now();
  return assetImageUrl(id, get(changeable) ? currentTimestamp : undefined);
});

const chainIconSize = computed(
  () => `${(Number.parseInt(get(size)) * 50) / 100}px`
);
const chainWrapperSize = computed(
  () => `${Number.parseInt(get(chainIconSize)) + 4}px`
);
const chainIconMargin = computed(() => `-${get(chainIconSize)}`);
const chainIconPosition = computed(() => {
  return `${(Number.parseInt(get(chainIconSize)) * 50) / 100}px`;
});

const placeholderStyle = computed(() => {
  const pad = get(padding);
  const width = get(size);
  const prop = `calc(${pad} + ${pad} + ${width})`;
  return {
    'min-width': prop,
    height: prop
  };
});

watch([symbol, changeable, identifier], (curr, prev) => {
  set(error, false);
  if (curr[1] !== prev[1]) {
    set(pending, true);
  }
});
</script>

<template>
  <div :class="css.placeholder" :style="placeholderStyle">
    <adaptive-wrapper :circle="circle" :padding="padding">
      <v-tooltip top open-delay="400" :disabled="noTooltip">
        <template #activator="{ on, attrs }">
          <div>
            <div
              v-if="showChain && chain"
              :class="{
                [css.circle]: true,
                [css.chain]: true
              }"
            >
              <evm-chain-icon :chain="chain" :size="chainIconSize" />
            </div>

            <div
              v-bind="attrs"
              :style="styled"
              class="d-flex"
              :class="{ [css.circle]: circle }"
              v-on="on"
            >
              <div :class="css.wrapper">
                <div v-if="pending" class="black--text">
                  <token-placeholder :size="size" />
                </div>
                <generated-icon
                  v-if="currency || error"
                  :custom-asset="isCustomAsset"
                  :asset="displayAsset"
                  :currency="!!currency"
                  :size="size"
                />
                <v-img
                  v-else
                  :src="url"
                  :max-height="size"
                  :min-height="size"
                  :max-width="size"
                  :min-width="size"
                  contain
                  @loadstart="pending = true"
                  @load="pending = false"
                  @error="
                    error = true;
                    pending = false;
                  "
                />
              </div>
            </div>
          </div>
        </template>
        <span>
          {{ t('asset_icon.tooltip', tooltip) }}
        </span>
      </v-tooltip>
    </adaptive-wrapper>
  </div>
</template>
<style module lang="scss">
.circle {
  border-radius: 50%;
  overflow: hidden;
}

.chain {
  border: 1px solid rgb(200, 200, 200);
  background-color: white;
  position: absolute;
  margin-top: v-bind(chainIconMargin);
  margin-left: v-bind(chainIconMargin);
  top: v-bind(chainIconPosition);
  left: v-bind(chainIconPosition);
  width: v-bind(chainWrapperSize);
  height: v-bind(chainWrapperSize);
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder {
  position: relative;
}

.wrapper {
  position: relative;
  width: v-bind(size);
  height: v-bind(size);

  > * {
    position: absolute;
    top: 0;
    left: 0;
  }
}
</style>
