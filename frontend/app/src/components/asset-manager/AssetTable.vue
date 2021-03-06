<template>
  <card outlined-body>
    <template #title>
      {{ $t('asset_table.assets') }}
    </template>
    <template #subtitle>
      {{ $t('asset_table.subtitle') }}
    </template>
    <template #search>
      <v-row justify="end" no-gutters>
        <v-col cols="12" sm="4">
          <v-text-field
            v-model="search"
            dense
            prepend-inner-icon="mdi-magnify"
            :label="$t('asset_table.search')"
            outlined
          />
        </v-col>
      </v-row>
    </template>
    <v-btn absolute fab top right dark color="primary" @click="add">
      <v-icon> mdi-plus </v-icon>
    </v-btn>
    <v-data-table
      :items="tokens"
      :loading="loading"
      :headers="headers"
      item-key="address"
      sort-by="name"
      :search.sync="search"
      :footer-props="footerProps"
    >
      <template #item.name="{ item }">
        <asset-details-base
          opens-details
          :asset="{
            ...item,
            symbol: item.identifier ? item.identifier : item.symbol
          }"
        />
      </template>
      <template #item.address="{ item }">
        <hash-link :text="item.address" />
      </template>
      <template #item.started="{ item }">
        <date-display :timestamp="item.started" />
      </template>
      <template #item.actions="{ item }">
        <row-actions
          :edit-tooltip="$t('asset_table.edit_tooltip')"
          :delete-tooltip="$t('asset_table.delete_tooltip')"
          @edit-click="edit(item)"
          @delete-click="deleteToken(item.address)"
        />
      </template>
      <template #item.expand="{ item }">
        <row-expander
          v-if="item.underlyingTokens && item.underlyingTokens.length > 0"
          :expanded="expanded.includes(item)"
          @click="expanded = expanded.includes(item) ? [] : [item]"
        />
      </template>
    </v-data-table>
  </card>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import { footerProps } from '@/config/datatable.common';
import { CustomEthereumToken } from '@/services/assets/types';

@Component({
  components: { RowActions, RowExpander, AssetDetailsBase }
})
export default class AssetTable extends Vue {
  @Prop({ required: true, type: Array })
  tokens!: CustomEthereumToken[];
  @Prop({ required: false, type: Boolean, default: false })
  loading!: string;

  @Emit()
  add() {}
  @Emit()
  edit(_token: CustomEthereumToken) {}
  @Emit()
  deleteToken(_address: string) {}

  expand = [];
  search: string = '';
  readonly footerProps = footerProps;
  readonly headers: DataTableHeader[] = [
    {
      text: this.$t('asset_table.headers.asset').toString(),
      value: 'name'
    },
    {
      text: this.$t('asset_table.headers.address').toString(),
      value: 'address'
    },
    {
      text: this.$t('asset_table.headers.coingecko').toString(),
      value: 'coingecko'
    },
    {
      text: this.$t('asset_table.headers.cryptocompare').toString(),
      value: 'cryptocompare'
    },
    {
      text: this.$t('asset_table.headers.started').toString(),
      value: 'started'
    },
    {
      text: '',
      value: 'actions'
    },
    {
      text: '',
      value: 'expand'
    }
  ];
}
</script>

<style scoped lang="scss"></style>
