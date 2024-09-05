<script setup lang="ts">
import { truncateAddress } from '@/utils/truncate';
import type { Suggestion } from '@/types/filtering';

const props = withDefaults(
  defineProps<{
    suggestion: Suggestion;
    chip?: boolean;
  }>(),
  {
    chip: false,
  },
);

const { suggestion } = toRefs(props);

const isBoolean = computed(() => {
  const item = get(suggestion);
  const value = item.value;

  return typeof value === 'boolean';
});

const { assetInfo } = useAssetInfoRetrieval();
const { getChainName } = useSupportedChains();

const asset = computed<{ identifier: string; symbol: string } | undefined>(() => {
  const item = get(suggestion);
  const value = item.value;

  if (!item.asset)
    return undefined;

  let usedAsset, identifier;
  if (typeof value === 'string') {
    identifier = value;
    usedAsset = get(assetInfo(value));
  }
  else {
    identifier = value.identifier;
    usedAsset = value;
  }

  if (!usedAsset)
    return undefined;

  let symbol = usedAsset.symbol;
  if (usedAsset.evmChain && !props.chip)
    symbol += ` (${get(getChainName(usedAsset.evmChain))})`;
  else if (usedAsset.isCustomAsset)
    symbol = usedAsset.name;

  return {
    identifier,
    symbol,
  };
});

const displayValue = computed(() => {
  const item = get(suggestion);
  const value = item.value;

  if (get(isBoolean))
    return `${value}`;

  return value;
});
</script>

<template>
  <span class="font-medium flex items-center">
    <span :class="{ 'text-rui-primary': !chip }">
      {{ suggestion.key }}
    </span>
    <template v-if="!(chip && isBoolean)">
      <span
        :class="{
          [$style.comparator]: chip,
          ['text-rui-primary']: !chip,
        }"
        class="px-1"
      >
        <span>{{ suggestion.exclude ? '!=' : '=' }}</span>
      </span>
      <div
        v-if="suggestion.asset && asset"
        class="flex items-center gap-2"
        :class="{ 'ml-2': !chip }"
      >
        <AssetIcon
          :identifier="asset.identifier"
          padding="1.5px"
          :size="chip ? '16px' : '18px'"
          :chain-icon-size="chip ? '9px' : '11px'"
          chain-icon-padding="0.5px"
        />
        <span class="font-normal text-sm">
          {{ asset.symbol }}
        </span>
      </div>
      <span
        v-else-if="displayValue"
        class="font-normal"
      >
        {{ truncateAddress(displayValue, 10) }}
      </span>
    </template>
  </span>
</template>

<style lang="scss" module>
.comparator {
  @apply py-0.5 border-l border-r border-white mx-1.5 flex items-center;
}

:global(.dark) {
  .comparator {
    @apply border-rui-grey-900 #{!important};
  }
}
</style>
