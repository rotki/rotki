<script setup lang="ts">
import { type LpType } from '@rotki/common/lib/defi';
import { type XswapPool } from '@rotki/common/lib/defi/xswap';

const props = withDefaults(
  defineProps<{
    pools: XswapPool[];
    type: LpType;
    value: string[];
    outlined?: boolean;
    dense?: boolean;
    noPadding?: boolean;
  }>(),
  {
    outlined: false,
    dense: false,
    noPadding: false
  }
);

const emit = defineEmits<{ (e: 'input', value: string[]): void }>();

const { value, type } = toRefs(props);
const input = (value: string[]) => emit('input', value);

const { getPoolName } = useLiquidityPosition();

const filter = (item: XswapPool, queryText: string) => {
  const searchString = queryText.toLocaleLowerCase();
  const name = getPoolName(get(type), item.assets).toLowerCase();
  return name.includes(searchString);
};

const remove = (asset: XswapPool) => {
  const addresses = [...get(value)];
  const index = addresses.indexOf(asset.address);
  addresses.splice(index, 1);
  input(addresses);
};

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
      :value="value"
      :label="t('liquidity_pool_selector.label')"
      :items="pools"
      :dense="dense"
      :outlined="outlined"
      :filter="filter"
      :menu-props="{ closeOnContentClick: true }"
      multiple
      clearable
      deletable-chips
      single-line
      hide-details
      hide-selected
      item-value="address"
      chips
      @input="input($event)"
    >
      <template #selection="data">
        <RuiChip
          class="font-medium"
          v-bind="data.attrs"
          closeable
          size="sm"
          :input-value="data.selected"
          @click="data.select"
          @click:close="remove(data.item)"
        >
          {{ getPoolName(type, data.item.assets) }}
        </RuiChip>
      </template>
      <template #item="{ item }">
        <span
          :id="`ua-${item.address.toLocaleLowerCase()}`"
          class="font-medium text-sm"
        >
          {{ getPoolName(type, item.assets) }}
        </span>
      </template>
    </VAutocomplete>
  </RuiCard>
</template>
