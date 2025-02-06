<script setup lang="ts">
import { useLiquidityPosition } from '@/composables/defi';
import type { LpType, XswapPool } from '@rotki/common';

const model = defineModel<string[]>({ required: true });

const props = withDefaults(
  defineProps<{
    pools: XswapPool[];
    type: LpType;
    dense?: boolean;
    noPadding?: boolean;
  }>(),
  {
    dense: false,
    noPadding: false,
  },
);

const { type } = toRefs(props);

const { getPoolName } = useLiquidityPosition();

function filter(item: XswapPool, queryText: string) {
  const searchString = queryText.toLocaleLowerCase();
  const name = getPoolName(get(type), item.assets).toLowerCase();
  return name.includes(searchString);
}

const { t } = useI18n();
</script>

<template>
  <RuiCard
    variant="flat"
    :no-padding="noPadding"
    rounded="sm"
    content-class="!overflow-visible"
  >
    <RuiAutoComplete
      v-model="model"
      :label="t('liquidity_pool_selector.label')"
      :options="pools"
      :dense="dense"
      variant="outlined"
      :filter="filter"
      clearable
      hide-details
      key-attr="address"
      chips
      hide-selected
      :item-height="44"
    >
      <template #selection="{ item }">
        {{ getPoolName(type, item.assets) }}
      </template>
      <template #item="{ item }">
        <div class="font-medium py-2">
          {{ getPoolName(type, item.assets) }}
        </div>
      </template>
    </RuiAutoComplete>
  </RuiCard>
</template>
