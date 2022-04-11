<template>
  <v-card v-bind="$attrs">
    <div
      :class="{
        'mx-4 pt-2': !noPadding
      }"
    >
      <v-autocomplete
        :value="value"
        :label="$t('liquidity_pool_selector.label')"
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
              {{ data.item.name }}
            </span>
          </v-chip>
        </template>
        <template #item="{ item }">
          <v-list-item-content
            :id="`ua-${item.address.toLocaleLowerCase()}`"
            class="font-weight-medium"
          >
            <v-list-item-title>
              {{ item.name }}
            </v-list-item-title>
          </v-list-item-content>
        </template>
      </v-autocomplete>
    </div>
  </v-card>
</template>

<script lang="ts">
import { Pool } from '@rotki/common/lib/defi/balancer';
import { defineComponent, PropType, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';

export default defineComponent({
  name: 'LiquidityPoolSelector',
  props: {
    pools: { required: true, type: Array as PropType<Pool[]> },
    value: { required: true, type: Array as PropType<string[]> },
    outlined: { required: false, type: Boolean, default: false },
    dense: { required: false, type: Boolean, default: false },
    noPadding: { required: false, type: Boolean, default: false }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { value } = toRefs(props);
    const input = (_value: string[]) => emit('input', _value);

    const filter = (item: Pool, queryText: string) => {
      const searchString = queryText.toLocaleLowerCase();
      const asset1 = item.name.toLocaleLowerCase();
      const asset2 = item.name.toLocaleLowerCase();
      const name = `${asset1}/${asset2}`;
      return name.indexOf(searchString) > -1;
    };

    const remove = (asset: Pool) => {
      const addresses = [...get(value)];
      const index = addresses.findIndex(address => address === asset.address);
      addresses.splice(index, 1);
      input(addresses);
    };

    return {
      filter,
      input,
      remove
    };
  }
});
</script>
