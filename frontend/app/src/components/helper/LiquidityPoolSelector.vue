<script setup lang="ts">
import type { LpType } from '@rotki/common/lib/defi';
import type { XswapPool } from '@rotki/common/lib/defi/xswap';

const props = withDefaults(
  defineProps<{
    pools: XswapPool[];
    type: LpType;
    modelValue: string[];
    outlined?: boolean;
    dense?: boolean;
    noPadding?: boolean;
  }>(),
  {
    outlined: false,
    dense: false,
    noPadding: false,
  },
);

const emit = defineEmits<{ (e: 'update:model-value', value: string[]): void }>();

const model = useSimpleVModel(props, emit);

const { type } = toRefs(props);

const { getPoolName } = useLiquidityPosition();

function filter(_value: string, queryText: string, itemValue?: { raw: XswapPool }) {
  const item = itemValue?.raw;
  if (!item)
    return false;

  const searchString = queryText.toLocaleLowerCase();
  const name = getPoolName(get(type), item.assets).toLowerCase();
  return name.includes(searchString);
}

function remove(asset: XswapPool) {
  const addresses = [...get(model)];
  const index = addresses.indexOf(asset.address);
  addresses.splice(index, 1);
  set(model, addresses);
}

const { t } = useI18n();
</script>

<template>
  <RuiCard
    variant="flat"
    :no-padding="noPadding"
    rounded="sm"
    class="[&>div:last-child]:overflow-hidden"
  >
    <VAutocomplete
      v-model="model"
      :label="t('liquidity_pool_selector.label')"
      :items="pools"
      :density="dense ? 'compact' : undefined"
      :outlined="outlined"
      :custom-filter="filter"
      :menu-props="{ closeOnContentClick: true }"
      multiple
      clearable
      closable-chips
      single-line
      hide-details
      hide-selected
      item-value="address"
      chips
    >
      <template #selection="{ item }">
        <RuiChip
          class="font-medium"
          closeable
          size="sm"
          @click="model = [...model, getPoolName(type, item.raw.assets)]"
          @click:close="remove(item.raw)"
        >
          {{ getPoolName(type, item.raw.assets) }}
        </RuiChip>
      </template>
      <template #item="{ item }">
        <span
          :id="`ua-${item.raw.address.toLocaleLowerCase()}`"
          class="font-medium text-sm"
        >
          {{ getPoolName(type, item.raw.assets) }}
        </span>
      </template>
    </VAutocomplete>
  </RuiCard>
</template>
