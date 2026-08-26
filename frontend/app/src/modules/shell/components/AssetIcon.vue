<script setup lang="ts">
import { Blockchain, getAddressFromEvmIdentifier, getIdentifierFromSymbolMap, isEvmIdentifier } from '@rotki/common';
import { useBlockie } from '@/modules/accounts/use-blockie';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { HYPERLIQUID_TOKEN, SOLANA_CHAIN, SOLANA_TOKEN } from '@/modules/assets/types';
import { useAssetIconCheck } from '@/modules/assets/use-asset-icon-check';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { isBlockchain } from '@/modules/core/common/chains';
import { hasAssetMetadata } from '@/modules/core/common/display/assets';
import { useCopy } from '@/modules/core/common/use-clipboard';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSetting } from '@/modules/settings/use-setting';
import AppImage from '@/modules/shell/components/AppImage.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import EvmChainIcon from '@/modules/shell/components/EvmChainIcon.vue';
import GeneratedIcon from '@/modules/shell/components/GeneratedIcon.vue';

interface AssetIconProps {
  identifier: string;
  size: string;
  noTooltip?: boolean;
  circle?: boolean;
  padding?: string;
  showChain?: boolean;
  flat?: boolean;
  resolutionOptions?: AssetResolutionOptions;
  chainIconSize?: string;
  forceChain?: string;
  /**
   * Disables scroll event listeners on tooltip popper for better performance in virtualized lists.
   * The tooltip still works on hover, but won't recalculate position during scroll.
   */
  optimizeForVirtualScroll?: boolean;
}

const {
  chainIconSize,
  circle,
  flat = false,
  forceChain,
  identifier,
  noTooltip = false,
  optimizeForVirtualScroll = false,
  padding = '2px',
  resolutionOptions = {},
  showChain = true,
  size,
} = defineProps<AssetIconProps>();

const emit = defineEmits<{ click: [] }>();

const { t } = useI18n({ useScope: 'global' });

const error = ref<boolean>(false);
const pending = ref<boolean>(true);
const abortController = ref<AbortController>();

const { getAssetIconUrl } = useAssetsStore();
const { getBlockie } = useBlockie();
const { getChainName } = useSupportedChains();
const { checkIfAssetExists } = useAssetIconCheck();
const { currencies } = useCurrencies();
const { useAssetInfo } = useAssetInfoRetrieval();
const shouldShowAmount = useSetting('shouldShowAmount');

const mappedIdentifier = computed<string>(() => {
  const id = getIdentifierFromSymbolMap(identifier);
  return isBlockchain(id) ? id.toUpperCase() : id;
});

const currency = computed<string | undefined>(() => {
  const id = get(mappedIdentifier);
  const fiatCurrencies = get(currencies).filter(({ crypto }) => !crypto);
  return fiatCurrencies.find(({ tickerSymbol }) => tickerSymbol === id)?.unicodeSymbol;
});

const asset = useAssetInfo(mappedIdentifier, () => resolutionOptions);
const url = reactify(getAssetIconUrl)(mappedIdentifier);

const isCustomAsset = computed(() => get(asset)?.isCustomAsset ?? false);

const chain = computed(() => {
  if (forceChain) {
    return forceChain;
  }

  const info = get(asset);
  if (!info) {
    return undefined;
  }
  if (info.evmChain) {
    return info.evmChain;
  }

  if (info.assetType === SOLANA_TOKEN) {
    return SOLANA_CHAIN;
  }

  if (info.assetType === HYPERLIQUID_TOKEN) {
    return Blockchain.HYPERLIQUID;
  }

  return undefined;
});
const symbol = computed(() => get(asset)?.symbol);
const name = computed(() => get(asset)?.name);
const protocol = computed<string | undefined>(() => {
  const protocol = get(asset)?.protocol;
  if (!protocol || protocol === 'spam') {
    return undefined;
  }
  return protocol;
});

const displayAsset = computed<string>(() => {
  const currencySymbol = get(currency);
  if (currencySymbol)
    return currencySymbol;

  return get(symbol) ?? get(name) ?? get(mappedIdentifier) ?? '';
});

/**
 * Whether the asset has anything to call itself by.
 *
 * @remarks
 * An asset with no metadata is still handed a name and a symbol, of the form `EVM Token: 0x…`.
 * Both are non-empty, so a plain `name ?? symbol` check reports "named" for exactly the assets that
 * have no name. Asked once here rather than in every consumer.
 */
const hasAssetText = computed<boolean>(() => {
  if (get(currency))
    return true;
  return hasAssetMetadata(identifier, get(symbol)) || hasAssetMetadata(identifier, get(name));
});

/**
 * Blockie for an asset with nothing to call itself by. Its `displayAsset` falls back to the raw
 * identifier, so the generated text mark reads `eip` for every unknown EVM asset alike. A blockie
 * of the contract address at least tells two unknowns apart. Contract addresses are not user
 * identities, so unlike an account blockie this one needs no scrambling.
 */
const blockie = computed<string | undefined>(() => {
  if (get(hasAssetText) || !isEvmIdentifier(identifier))
    return undefined;
  const address = getAddressFromEvmIdentifier(identifier);
  return address ? getBlockie(address) : undefined;
});

// Without it the tooltip's `[{symbol}] {name}` renders as a bare `[]`; the address block below
// still carries the useful part.
const hasTooltipText = hasAssetText;

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

// Popper options - disable scroll listeners for virtualized lists to prevent reflow during scroll
const popperOptions = computed(() => ({
  placement: 'top' as const,
  scroll: !optimizeForVirtualScroll,
  resize: !optimizeForVirtualScroll,
}));

const usedChainIconSize = computed(() => chainIconSize || `${(Number.parseInt(size) * 50) / 100}px`);
const usedProtocolIconSize = computed(() => chainIconSize || `${(Number.parseInt(size) * 40) / 100}px`);

const chainIconMargin = computed(() => `-${get(usedChainIconSize)}`);

const placeholderStyle = computed(() => {
  const prop = `calc(${padding} + ${padding} + ${size})`;
  return {
    height: prop,
    width: prop,
  };
});

watchImmediate(mappedIdentifier, async (identifier) => {
  set(pending, true);
  set(error, false);

  // Fiat currencies render via their unicode symbol — no icon fetch needed.
  if (isDefined(currency)) {
    set(pending, false);
    return;
  }

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

const { copied, copy } = useCopy(() => identifier);
</script>

<template>
  <RuiTooltip
    :popper="popperOptions"
    :open-delay="400"
    :disabled="noTooltip || !shouldShowAmount"
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
          class="!rounded-full !overflow-hidden bg-white z-[1] absolute flex items-center justify-center shadow-sm -bottom-1 -right-1 border border-rui-grey-300 dark:border-rui-grey-900"
          :style="{ marginTop: chainIconMargin, marginLeft: chainIconMargin }"
        >
          <EvmChainIcon
            :chain="chain"
            :size="usedChainIconSize"
          />
        </div>

        <div
          v-if="protocol"
          class="z-[1] absolute -top-1 -left-1 border border-rui-grey-300 dark:border-rui-grey-900 rounded-md bg-white"
          :class="{ blur: !shouldShowAmount }"
        >
          <CounterpartyDisplay
            :counterparty="protocol"
            :size="usedProtocolIconSize"
            icon
          />
        </div>

        <div
          class="flex items-center justify-center cursor-pointer h-full w-full icon-bg"
          :class="{
            '!rounded-full !overflow-hidden': circle,
            'blur': !shouldShowAmount,
          }"
        >
          <!-- An asset with no symbol and no name has no icon worth waiting on either: its
               blockie IS the identity, so it renders instead of the image rather than only when
               the image fails. Otherwise a placeholder served by the icon endpoint would keep the
               fallback from ever running. -->
          <GeneratedIcon
            v-if="blockie"
            :blockie="blockie"
            :size="size"
            :flat="flat"
          />

          <GeneratedIcon
            v-else-if="!currency && pending"
            class="absolute"
            :custom-asset="isCustomAsset"
            :asset="displayAsset"
            :size="size"
            :flat="flat"
          />

          <GeneratedIcon
            v-else-if="currency || error"
            :custom-asset="isCustomAsset"
            :asset="displayAsset"
            :size="size"
            :flat="flat"
          />

          <AppImage
            v-else
            v-show="!pending && !error"
            :class="{ 'rounded-full overflow-hidden': flat }"
            fit="contain"
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

    <div v-if="hasTooltipText">
      {{ t('asset_icon.tooltip', tooltip) }}
    </div>

    <!-- Chain and protocol otherwise live only in the corner badges, a few pixels across. For an
         asset with no symbol and no name they are the only context the tooltip can offer beyond
         the address. -->
    <div
      v-if="chain || protocol"
      class="flex items-center gap-3"
    >
      <span
        v-if="chain"
        class="flex items-center gap-1.5"
      >
        <EvmChainIcon
          :chain="chain"
          size="14px"
        />
        {{ getChainName(chain) }}
      </span>
      <!-- It hardcodes `text-rui-text`, the light-background colour, which is unreadable on the
           tooltip's dark surface. Same specificity, so the override needs `!`. -->
      <CounterpartyDisplay
        v-if="protocol"
        :counterparty="protocol"
        size="14px"
        class="!text-inherit"
      />
    </div>
    <template v-if="isEvmIdentifier(identifier)">
      <div class="overflow-hidden h-5">
        <div
          class="transition-all duration-100"
          :class="{
            '-mt-5': copied,
          }"
        >
          <div class="h-5 font-mono flex items-center gap-2">
            {{ getAddressFromEvmIdentifier(identifier) }}
            <RuiButton
              size="sm"
              variant="text"
              icon
              @click="copy()"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-copy"
                  size="12"
                  class="!text-rui-grey-400"
                />
              </template>
            </RuiButton>
          </div>
        </div>
        <div class="font-bold text-caption uppercase text-rui-success-lighter">
          {{ t('amount_display.copied') }}
        </div>
      </div>
    </template>
  </RuiTooltip>
</template>
