<script setup lang="ts">
import { type Suggestion } from '@/types/filtering';
import { truncateAddress } from '@/utils/truncate';

const props = withDefaults(
  defineProps<{
    suggestion: Suggestion;
    chip?: boolean;
  }>(),
  {
    chip: false
  }
);

const { suggestion } = toRefs(props);

const { assetInfo } = useAssetInfoRetrieval();

const isBoolean = computed(() => {
  const item = get(suggestion);
  const value = item.value;

  return typeof value === 'boolean';
});

const displayValue = computed(() => {
  const item = get(suggestion);
  const value = item.value;

  if (get(isBoolean)) {
    return `${value}`;
  }

  if (!item.asset) {
    return value;
  }

  let usedAsset = value;
  if (typeof usedAsset === 'string') {
    usedAsset = get(assetInfo(value));
  }

  if (!usedAsset) {
    return value;
  }

  if (usedAsset.evmChain) {
    return `${usedAsset.symbol} (${usedAsset.evmChain})`;
  }

  return usedAsset.isCustomAsset ? usedAsset.name : usedAsset.symbol;
});

const css = useCssModule();
</script>

<template>
  <span class="font-medium flex items-center">
    <span :class="{ 'text-rui-primary': !chip }">
      {{ suggestion.key }}
    </span>
    <template v-if="!(chip && isBoolean)">
      <span
        :class="{
          [css.comparator]: chip,
          ['text-rui-primary']: !chip
        }"
        class="px-1"
      >
        <span>{{ suggestion.exclude ? '!=' : '=' }}</span>
      </span>
      <span class="font-normal">
        {{ truncateAddress(displayValue, 10) }}
      </span>
    </template>
  </span>
</template>

<style lang="scss" module>
.comparator {
  @apply py-1.5 border-l border-r border-white mx-1.5 flex items-center;
}

:global(.dark) {
  .comparator {
    @apply border-rui-grey-900 #{!important};
  }
}
</style>
