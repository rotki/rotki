<template>
  <v-card v-bind="$attrs">
    <div class="mx-4 pt-2">
      <v-autocomplete
        :value="value"
        :items="pools"
        multiple
        clearable
        deletable-chips
        :label="$t('liquidity_pool_selector.label')"
        :filter="filter"
        item-value="address"
        chips
        :menu-props="{ closeOnContentClick: true }"
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
    <v-card-text>
      <slot />
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Pool } from '@rotki/common/lib/defi/balancer';
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({
  name: 'LiquidityPoolSelector'
})
export default class LiquidityPoolSelector extends Vue {
  @Prop({ required: true })
  pools!: Pool[];
  @Prop({ required: true, type: Array })
  value!: string[];
  @Emit()
  input(_value: string[]) {}

  filter(item: Pool, queryText: string) {
    const searchString = queryText.toLocaleLowerCase();
    const asset1 = item.name.toLocaleLowerCase();
    const asset2 = item.name.toLocaleLowerCase();
    const name = `${asset1}/${asset2}`;
    return name.indexOf(searchString) > -1;
  }

  remove(asset: Pool) {
    const addresses = [...this.value];
    const index = addresses.findIndex(address => address === asset.address);
    addresses.splice(index, 1);
    this.input(addresses);
  }
}
</script>
