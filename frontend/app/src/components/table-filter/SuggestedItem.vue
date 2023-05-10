<script setup lang="ts">
import { type Suggestion } from '@/types/filtering';
import { truncateAddress } from '@/filters';

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

const displayValue = computed(() => {
  const item = get(suggestion);

  const value = item.value;
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
const { dark } = useTheme();
</script>

<template>
  <span class="font-weight-medium d-flex align-center">
    <span>
      {{ suggestion.key }}
    </span>
    <span
      :class="{
        [css.comparator]: chip,
        [css['comparator--dark']]: dark
      }"
      class="px-1 font-weight-bold"
    >
      <span>{{ suggestion.exclude ? '!=' : '=' }}</span>
    </span>
    <span>
      {{ truncateAddress(displayValue, 10) }}
    </span>
  </span>
</template>

<style lang="scss" module>
.comparator {
  padding: 6px 4px;
  border-color: white;
  border-style: solid;
  border-left-width: 1px;
  border-right-width: 1px;
  margin: 0 6px;
  display: flex;
  align-items: center;

  &--dark {
    border-color: var(--v-rotki-light-grey-base);
  }
}
</style>
