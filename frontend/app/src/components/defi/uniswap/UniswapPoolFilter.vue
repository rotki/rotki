<template>
  <v-card v-bind="$attrs">
    <div
      :class="{
        'mx-4 pt-2': !noPadding
      }"
    >
      <v-autocomplete
        :value="value"
        :items="poolAssets"
        :label="t('liquidity_pool_selector.label')"
        :filter="filter"
        :dense="dense"
        :outlined="outlined"
        :menu-props="{ closeOnContentClick: true }"
        item-value="address"
        chips
        multiple
        clearable
        deletable-chips
        single-line
        hide-details
        hide-selected
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
                t('uniswap.pool_header', {
                  version,
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
                t('uniswap.pool_header', {
                  version,
                  asset1: getSymbol(item.assets[0]),
                  asset2: getSymbol(item.assets[1])
                })
              }}
            </v-list-item-title>
          </v-list-item-content>
        </template>
      </v-autocomplete>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { XswapPool } from '@rotki/common/lib/defi/xswap';
import { get } from '@vueuse/core';
import { PropType, toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { useAssetInfoRetrieval } from '@/store/assets';

const props = defineProps({
  value: { required: true, type: Array as PropType<string[]> },
  outlined: { required: false, type: Boolean, default: false },
  dense: { required: false, type: Boolean, default: false },
  noPadding: { required: false, type: Boolean, default: false },
  poolAssets: { required: true, type: Array as PropType<XswapPool[]> },
  version: {
    required: false,
    type: String as PropType<'2' | '3'>,
    default: '2'
  }
});

const emit = defineEmits(['input']);
const { value } = toRefs(props);
const { getAssetSymbol: getSymbol } = useAssetInfoRetrieval();

const input = (value: string[]) => {
  emit('input', value);
};

const filter = (item: XswapPool, queryText: string) => {
  const searchString = queryText.toLocaleLowerCase();
  const asset1 = getSymbol(item.assets[0]).toLocaleLowerCase();
  const asset2 = getSymbol(item.assets[1]).toLocaleLowerCase();
  const name = `${asset1}/${asset2}`;
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
