<script setup lang="ts">
import type { StyleValue } from 'vue';
import AppImage from '@/components/common/AppImage.vue';
import EvmChainIcon from '@/components/helper/display/icons/EvmChainIcon.vue';
import GeneratedIcon from '@/components/helper/display/icons/GeneratedIcon.vue';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useCopy } from '@/composables/copy';
import { useAssetIconStore } from '@/store/assets/icon';
import { isBlockchain } from '@/types/blockchain/chains';
import { useCurrencies } from '@/types/currencies';
import { getAddressFromEvmIdentifier, getIdentifierFromSymbolMap, isEvmIdentifier } from '@rotki/common';

interface AssetIconProps {
  identifier: string;
  size: string;
  styled?: StyleValue;
  noTooltip?: boolean;
  circle?: boolean;
  padding?: string;
  chainIconPadding?: string;
  enableAssociation?: boolean;
  showChain?: boolean;
  flat?: boolean;
  resolutionOptions?: AssetResolutionOptions;
  chainIconSize?: string;
  forceChain?: string;
}

const props = withDefaults(defineProps<AssetIconProps>(), {
  chainIconPadding: '0.5px',
  circle: false,
  enableAssociation: true,
  flat: false,
  forceChain: undefined,
  noTooltip: false,
  padding: '2px',
  resolutionOptions: () => ({}),
  showChain: true,
  styled: undefined,
});

const emit = defineEmits<{ click: [] }>();

const { t } = useI18n({ useScope: 'global' });

const { chainIconSize, identifier, padding, resolutionOptions, showChain, size } = toRefs(props);

const error = ref<boolean>(false);
const pending = ref<boolean>(true);
const abortController = ref<AbortController>();

const { checkIfAssetExists, getAssetImageUrl } = useAssetIconStore();
const { currencies } = useCurrencies();
const { assetInfo } = useAssetInfoRetrieval();

const mappedIdentifier = computed<string>(() => {
  const id = getIdentifierFromSymbolMap(get(identifier));
  return isBlockchain(id) ? id.toUpperCase() : id;
});

const currency = computed<string | undefined>(() => {
  const id = get(mappedIdentifier);
  const fiatCurrencies = get(currencies).filter(({ crypto }) => !crypto);
  return fiatCurrencies.find(({ tickerSymbol }) => tickerSymbol === id)?.unicodeSymbol;
});

const asset = assetInfo(mappedIdentifier, resolutionOptions);
const url = reactify(getAssetImageUrl)(mappedIdentifier);

const isCustomAsset = computed(() => get(asset)?.isCustomAsset ?? false);

const chain = computed(() => props.forceChain || get(asset)?.evmChain);
const symbol = computed(() => get(asset)?.symbol);
const name = computed(() => get(asset)?.name);

const displayAsset = computed<string>(() => {
  const currencySymbol = get(currency);
  if (currencySymbol)
    return currencySymbol;

  return get(symbol) ?? get(name) ?? get(mappedIdentifier) ?? '';
});

const tooltip = computed(() => {
  const assetName = get(name) ?? '';
  const assetSymbol = get(symbol) ?? '';
  const isCustom = get(isCustomAsset);

  const emptyNameAsset = (symbol: string) => ({
    name: '',
    symbol,
  });

  if (isCustom) {
    return emptyNameAsset(assetName);
  }

  const areSymbolAndNameEqual = assetName.toLowerCase() === assetSymbol.toLowerCase();
  if (areSymbolAndNameEqual) {
    return emptyNameAsset(assetSymbol);
  }

  return {
    name: assetName,
    symbol: assetSymbol,
  };
});

const usedChainIconSize = computed(() => get(chainIconSize) || `${(Number.parseInt(get(size)) * 50) / 100}px`);

const chainIconMargin = computed(() => `-${get(usedChainIconSize)}`);

const placeholderStyle = computed(() => {
  const pad = get(padding);
  const width = get(size);
  const prop = `calc(${pad} + ${pad} + ${width})`;
  return {
    height: prop,
    width: prop,
  };
});

watchImmediate(mappedIdentifier, async (identifier) => {
  set(pending, true);
  set(error, false);

  if (isDefined(abortController)) {
    get(abortController).abort();
  }
  set(abortController, new AbortController());

  const assetExists = await checkIfAssetExists(identifier, {
    abortController: get(abortController),
  });

  set(pending, false);
  if (!assetExists) {
    set(error, true);
  }
});

const { copy } = useCopy(identifier);
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="400"
    :disabled="noTooltip"
    persist-on-tooltip-hover
  >
    <template #activator>
      <div
        class="relative"
        :style="placeholderStyle"
        @click="emit('click')"
      >
        <div
          v-if="showChain && chain"
          class="chain"
          :class="{
            [$style.circle]: true,
            [$style.chain]: true,
          }"
        >
          <EvmChainIcon
            :chain="chain"
            :size="usedChainIconSize"
          />
        </div>

        <div
          :style="styled"
          class="flex items-center justify-center cursor-pointer h-full w-full icon-bg"
          :class="{
            [$style.circle]: circle,
          }"
        >
          <GeneratedIcon
            v-if="!currency && pending"
            class="absolute"
            :custom-asset="isCustomAsset"
            :asset="displayAsset"
            :size="size"
            :flat="flat"
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
            v-show="!pending && !error"
            :class="{ 'rounded-full overflow-hidden': flat }"
            contain
            :alt="displayAsset"
            :src="url"
            :loading="pending"
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

    <div>
      {{ t('asset_icon.tooltip', tooltip) }}
    </div>
    <div
      v-if="isEvmIdentifier(identifier)"
      class="font-mono flex items-center gap-2 -my-1"
    >
      {{ (isEvmIdentifier(identifier) ? getAddressFromEvmIdentifier(identifier) : identifier) }}
      <RuiButton
        size="sm"
        variant="text"
        icon
        @click="copy()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-copy"
            size="16"
            class="!text-rui-grey-400"
          />
        </template>
      </RuiButton>
    </div>
  </RuiTooltip>
</template>

<style module lang="scss">
.circle {
  @apply rounded-full overflow-hidden #{!important};
}

.chain {
  @apply bg-white absolute z-[1] flex items-center justify-center rounded-lg shadow-sm;
  @apply border border-rui-grey-200;
  margin-top: v-bind(chainIconMargin);
  margin-left: v-bind(chainIconMargin);
  bottom: -4px;
  right: -4px;
}

:global(.dark) {
  .chain {
    @apply border-rui-grey-900;
  }
}
</style>
