<template>
  <v-card v-bind="$attrs">
    <div
      :class="{
        'mx-4 pt-2': !noPadding
      }"
    >
      <v-autocomplete
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
        @input="input"
      >
        <template #selection="data">
          <v-chip
            outlined
            class="pa-2"
            v-bind="data.attrs"
            close
            :input-value="data.selected"
            @click="data.select"
            @click:close="remove(data.item)"
          >
            <span class="font-weight-medium">
              {{ getPoolName(type, data.item.assets) }}
            </span>
          </v-chip>
        </template>
        <template #item="{ item }">
          <v-list-item-content
            :id="`ua-${item.address.toLocaleLowerCase()}`"
            class="font-weight-medium"
          >
            <v-list-item-title>
              {{ getPoolName(type, item.assets) }}
            </v-list-item-title>
          </v-list-item-content>
        </template>
      </v-autocomplete>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { LpType } from '@rotki/common/lib/defi';
import { XswapPool } from '@rotki/common/lib/defi/xswap';
import { PropType } from 'vue';
import { setupLiquidityPosition } from '@/composables/defi';

const props = defineProps({
  pools: { required: true, type: Array as PropType<XswapPool[]> },
  value: { required: true, type: Array as PropType<string[]> },
  outlined: { required: false, type: Boolean, default: false },
  dense: { required: false, type: Boolean, default: false },
  noPadding: { required: false, type: Boolean, default: false },
  type: { required: true, type: String as PropType<LpType> }
});

const emit = defineEmits(['input']);
const { value, type } = toRefs(props);
const input = (_value: string[]) => emit('input', _value);

const { getPoolName } = setupLiquidityPosition();

const filter = (item: XswapPool, queryText: string) => {
  const searchString = queryText.toLocaleLowerCase();
  const name = getPoolName(get(type), item.assets).toLowerCase();
  return name.indexOf(searchString) > -1;
};

const remove = (asset: XswapPool) => {
  const addresses = [...get(value)];
  const index = addresses.findIndex(address => address === asset.address);
  addresses.splice(index, 1);
  input(addresses);
};

const { t } = useI18n();
</script>
