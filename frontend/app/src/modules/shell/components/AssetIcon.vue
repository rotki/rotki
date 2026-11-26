<script setup lang="ts">
import type { AssetResolutionOptions } from '@/modules/assets/use-asset-info-retrieval';
import { getAddressFromEvmIdentifier, isEvmIdentifier } from '@rotki/common';
import { RuiButton, RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { isDefined, reactify, watchImmediate } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAssetIconCheck } from '@/modules/assets/use-asset-icon-check';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useCopy } from '@/modules/core/common/use-clipboard';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSetting } from '@/modules/settings/use-setting';
import {
  assetChain,
  assetTooltip,
  type AssetTooltip,
  badgeCutoutMask,
  badgeSize,
  visibleProtocol,
} from '@/modules/shell/components/asset-icon-display';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import EvmChainIcon from '@/modules/shell/components/EvmChainIcon.vue';
import GeneratedIcon from '@/modules/shell/components/GeneratedIcon.vue';
import IconMark from '@/modules/shell/components/IconMark.vue';
import { useAssetIconIdentity } from '@/modules/shell/components/use-asset-icon-identity';

interface AssetIconProps {
  identifier: string;
  size: string;
  noTooltip?: boolean;
  circle?: boolean;
  padding?: string;
  showChain?: boolean;
  /** Leaves out the token's protocol mark, for icons that already sit beside one of their own. */
  hideProtocol?: boolean;
  resolutionOptions?: AssetResolutionOptions;
  chainIconSize?: string;
  forceChain?: string;
  /**
   * Disables the tooltip's ancestor scroll and resize listeners, for performance in virtualized
   * lists. The tooltip still opens on hover, but will not recalculate its position during scroll.
   */
  optimizeForVirtualScroll?: boolean;
}

const {
  chainIconSize,
  circle,
  forceChain,
  hideProtocol = false,
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
const { getChainName } = useSupportedChains();
const { checkIfAssetExists } = useAssetIconCheck();
const shouldShowAmount = useSetting('shouldShowAmount');

const {
  asset,
  blockie,
  currency,
  displayAsset,
  hasAssetText,
  isCustomAsset,
  mappedIdentifier,
  name,
  symbol,
} = useAssetIconIdentity(() => identifier, () => resolutionOptions);

const url = reactify(getAssetIconUrl)(mappedIdentifier);

const chain = computed<string | undefined>(() => assetChain(forceChain, get(asset)));
const protocol = computed<string | undefined>(() => visibleProtocol(get(asset)?.protocol));

/**
 * Gates the tooltip's `[{symbol}] {name}` line, which without any asset text renders as a bare `[]`.
 * The address block below it still carries the useful part.
 */
const hasTooltipText = hasAssetText;

const tooltip = computed<AssetTooltip>(() => assetTooltip(get(name), get(symbol), get(isCustomAsset)));

const tooltipOptions = computed(() => ({
  autoUpdate: {
    resize: !optimizeForVirtualScroll,
    scroll: !optimizeForVirtualScroll,
  },
  placement: 'top' as const,
}));

/** Both badges share one size, so a chain and a protocol read as the same kind of mark. */
const usedChainIconSize = computed<string>(() => badgeSize(chainIconSize, size, 40));
const usedProtocolIconSize = computed<string>(() => get(usedChainIconSize));

const chainBadge = computed<string | undefined>(() => (showChain ? get(chain) : undefined));
const protocolBadge = computed<string | undefined>(() => (hideProtocol ? undefined : get(protocol)));

const iconMaskStyle = computed<{ mask?: string; maskComposite?: string }>(() => {
  const mask = badgeCutoutMask(get(usedChainIconSize), {
    bottomRight: !!get(chainBadge),
    topLeft: !!get(protocolBadge),
  });
  return mask ? { mask, maskComposite: 'intersect' } : {};
});

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

  // Fiat currencies render via their unicode symbol. No icon fetch needed.
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
    :options="tooltipOptions"
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
          v-if="chainBadge"
          class="rounded-full! overflow-hidden! bg-white z-1 absolute flex items-center justify-center bottom-0 right-0"
        >
          <EvmChainIcon
            :chain="chainBadge"
            :size="usedChainIconSize"
          />
        </div>

        <div
          v-if="protocolBadge"
          class="z-1 absolute flex items-center justify-center top-0 left-0 rounded-full overflow-hidden bg-white"
          :class="{ blur: !shouldShowAmount }"
        >
          <CounterpartyDisplay
            :counterparty="protocolBadge"
            :size="usedProtocolIconSize"
            icon
          />
        </div>

        <div
          class="flex items-center justify-center cursor-pointer h-full w-full"
          :class="{
            'rounded-full! overflow-hidden!': circle,
            'blur': !shouldShowAmount,
          }"
          :style="{ padding, ...iconMaskStyle }"
        >
          <GeneratedIcon
            v-if="blockie"
            :blockie="blockie"
            :size="size"
          />

          <GeneratedIcon
            v-else-if="!currency && pending"
            class="absolute"
            :custom-asset="isCustomAsset"
            :asset="displayAsset"
            :identifier="mappedIdentifier"
            :size="size"
          />

          <GeneratedIcon
            v-else-if="currency || error"
            :custom-asset="isCustomAsset"
            :asset="displayAsset"
            :identifier="mappedIdentifier"
            :size="size"
          />

          <IconMark
            v-else
            v-show="!pending && !error"
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

    <div v-if="hasTooltipText">
      {{ t('asset_icon.tooltip', { ...tooltip }) }}
    </div>
    <div
      v-else-if="!isEvmIdentifier(identifier) && !chain && !protocol"
      class="font-mono"
    >
      {{ identifier }}
    </div>

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
      <CounterpartyDisplay
        v-if="protocol"
        :counterparty="protocol"
        size="14px"
        class="text-inherit!"
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
                  class="text-rui-grey-400!"
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
