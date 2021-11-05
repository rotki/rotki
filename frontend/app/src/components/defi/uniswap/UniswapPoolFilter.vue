<template>
  <v-card v-bind="$attrs">
    <div class="mx-4 pt-2">
      <v-autocomplete
        :value="value"
        :items="uniswapAssets"
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
              {{
                $t('uniswap.pool_header', {
                  asset1: getSymbol(data.item.assets[0]),
                  asset2: getSymbol(data.item.assets[1])
                })
              }}
            </span>
          </v-chip>
        </template>
        <template #item="{ item }">
          <v-list-item-content
            :id="`ua-${item.address.toLocaleLowerCase()}`"
            class="font-weight-medium"
          >
            <v-list-item-title>
              {{
                $t('uniswap.pool_header', {
                  asset1: getSymbol(item.assets[0]),
                  asset2: getSymbol(item.assets[1])
                })
              }}
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
import { XswapPool } from '@rotki/common/lib/defi/xswap';
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import AssetMixin from '@/mixins/asset-mixin';
import { GETTER_UNISWAP_ASSETS } from '@/store/defi/const';

@Component({
  computed: {
    ...mapGetters('defi', [GETTER_UNISWAP_ASSETS])
  }
})
export default class UniswapPoolFilter extends Mixins(AssetMixin) {
  uniswapAssets!: XswapPool[];
  @Prop({ required: true, type: Array })
  value!: string[];
  @Emit()
  input(_value: string[]) {}

  filter(item: XswapPool, queryText: string) {
    const searchString = queryText.toLocaleLowerCase();
    const asset1 = this.getSymbol(item.assets[0]).toLocaleLowerCase();
    const asset2 = this.getSymbol(item.assets[1]).toLocaleLowerCase();
    const name = `${asset1}/${asset2}`;
    return name.indexOf(searchString) > -1;
  }

  remove(asset: XswapPool) {
    const addresses = [...this.value];
    const index = addresses.findIndex(address => address === asset.address);
    addresses.splice(index, 1);
    this.input(addresses);
  }
}
</script>
