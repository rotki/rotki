<script setup lang="ts">
import { getIdentifierFromSymbolMap } from '@rotki/common';
import { useCurrencies } from '@/types/currencies';
import { isBlockchain } from '@/types/blockchain/chains';
import type { StyleValue } from 'vue';

const props = withDefaults(
  defineProps<{
    identifier: string;
    size: string;
    styled?: StyleValue;
    noTooltip?: boolean;
    circle?: boolean;
    padding?: string;
    enableAssociation?: boolean;
    showChain?: boolean;
    flat?: boolean;
  }>(),
  {
    styled: undefined,
    noTooltip: false,
    circle: false,
    padding: '2px',
    enableAssociation: true,
    showChain: true,
    flat: false,
  },
);

const emit = defineEmits<{ (e: 'click'): void }>();

const { t } = useI18n();

const { identifier, padding, size, enableAssociation, showChain } = toRefs(props);

const error = ref<boolean>(false);
const pending = ref<boolean>(true);

const css = useCssModule();

const { currencies } = useCurrencies();

const mappedIdentifier = computed<string>(() => {
  const id = getIdentifierFromSymbolMap(get(identifier));
  return isBlockchain(id) ? id.toUpperCase() : id;
});

const currency = computed<string | undefined>(() => {
  const id = get(mappedIdentifier);

  const fiatCurrencies = get(currencies).filter(({ crypto }) => !crypto);
  return fiatCurrencies.find(({ tickerSymbol }) => tickerSymbol === id)?.unicodeSymbol;
});

const { assetInfo } = useAssetInfoRetrieval();
const { getAssetImageUrl } = useAssetIconStore();

const asset = assetInfo(mappedIdentifier, enableAssociation);
const isCustomAsset = computed(() => get(asset)?.isCustomAsset ?? false);
const chain = computed(() => get(asset)?.evmChain);
const symbol = computed(() => get(asset)?.symbol);
const name = computed(() => get(asset)?.name);

const displayAsset = computed<string>(() => {
  const currencySymbol = get(currency);
  if (currencySymbol)
    return currencySymbol;

  return get(symbol) ?? get(name) ?? get(mappedIdentifier) ?? '';
});

const tooltip = computed(() => {
  if (get(isCustomAsset)) {
    return {
      symbol: get(name),
      name: '',
    };
  }

  return {
    symbol: get(symbol),
    name: get(name),
  };
});

const url = reactify(getAssetImageUrl)(mappedIdentifier);

const chainIconSize = computed(() => `${(Number.parseInt(get(size)) * 50) / 100}px`);
const chainWrapperSize = computed(() => `${Number.parseInt(get(chainIconSize)) + 4}px`);
const chainIconMargin = computed(() => `-${get(chainIconSize)}`);
const chainIconPosition = computed(() => `${(Number.parseInt(get(chainIconSize)) * 50) / 100}px`);

const placeholderStyle = computed(() => {
  const pad = get(padding);
  const width = get(size);
  const prop = `calc(${pad} + ${pad} + ${width})`;
  return {
    width: prop,
    height: prop,
  };
});

watch([symbol, identifier], () => {
  set(error, false);
});
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="400"
    :disabled="noTooltip"
  >
    <template #activator>
      <div
        class="relative"
        :style="placeholderStyle"
        @click="emit('click')"
      >
        <div
          v-if="showChain && chain"
          :class="{
            [css.circle]: true,
            [css.chain]: true,
          }"
        >
          <EvmChainIcon
            :chain="chain"
            :size="chainIconSize"
          />
        </div>

        <div
          :style="styled"
          class="flex items-center justify-center cursor-pointer h-full w-full icon-bg"
          :class="{ [css.circle]: circle }"
        >
          <RuiIcon
            v-if="!currency && pending"
            name="coin-line"
            :size="size"
            class="text-rui-light-text-secondary text-black absolute"
          />

          <GeneratedIcon
            v-if="currency || error"
            :custom-asset="isCustomAsset"
            :asset="displayAsset"
            :size="size"
            :flat="flat"
          />

          <AppImage
            v-else
            contain
            :alt="displayAsset"
            :src="url"
            :size="size"
            @loadstart="pending = true"
            @load="pending = false"
            @error="
              error = true;
              pending = false;
            "
          />
        </div>
      </div>
    </template>

    {{ t('asset_icon.tooltip', tooltip) }}
  </RuiTooltip>
</template>

<style module lang="scss">
.circle {
  @apply rounded-full overflow-hidden #{!important};
}

.chain {
  @apply border bg-white absolute z-[1] flex items-center justify-center;
  margin-top: v-bind(chainIconMargin);
  margin-left: v-bind(chainIconMargin);
  top: v-bind(chainIconPosition);
  left: v-bind(chainIconPosition);
  width: v-bind(chainWrapperSize);
  height: v-bind(chainWrapperSize);
}
</style>
