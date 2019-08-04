<template>
  <v-container>
    <v-layout>
      <v-flex>
        <h1 class="page-header">Dashboard</h1>
      </v-flex>
    </v-layout>
    <v-layout>
      <v-flex xs12>
        <exchange-box
          v-for="exchange in exchanges"
          :key="exchange.name"
          :name="exchange.name"
          :amount="exchange.total"
        ></exchange-box>
        <information-box
          v-if="blockchainTotal > 0"
          id="blockchain_box"
          icon="fa-hdd-o"
          :amount="blockchainTotal"
        ></information-box>
        <information-box
          v-if="fiatTotal > 0"
          id="banks_box"
          icon="fa-university"
          :amount="fiatTotal"
        ></information-box>
      </v-flex>
    </v-layout>
    <v-layout>
      <v-flex xs12>
        <h1 class="page-header">All Balances</h1>
      </v-flex>
    </v-layout>
    <v-layout>
      <v-flex xs12>
        <v-data-table
          :headers="headers"
          :items="blockchainTotals"
          :search="search"
        >
          <template #items="props">
            <td>{{ props.item.asset }}</td>
            <td class="text-right">
              {{ props.item.amount | precision(floatingPrecision) }}
            </td>
            <td class="text-right">
              {{ props.item.usd_value | precision(floatingPrecision) }}
            </td>
            <td class="text-right">
              {{ props.item.usd_value | percentage(total, floatingPrecision) }}
            </td>
          </template>
          <template #no-results>
            <v-alert :value="true" color="error" icon="warning">
              Your search for "{{ search }}" found no results.
            </v-alert>
          </template>
        </v-data-table>
      </v-flex>
    </v-layout>
    <v-layout>
      <div id="dashboard-wrapper">
        <div class="row">
          <div id="dashboard-contents" class="col-lg-12"></div>
        </div>
      </div>
    </v-layout>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import InformationBox from '@/components/InformationBox.vue';
import { mapGetters, mapState } from 'vuex';
import { Balances, ExchangeInfo } from '@/typing/types';
import { AssetBalance } from '@/model/asset-balance';
import ExchangeBox from '@/components/dashboard/ExchangeBox.vue';

@Component({
  components: { ExchangeBox, InformationBox },
  computed: {
    ...mapGetters(['blockchainTotals', 'floatingPrecision', 'exchanges']),
    ...mapState(['fiatTotal', 'blockchainTotal'])
  }
})
export default class Dashboard extends Vue {
  fiatTotal!: number;
  blockchainTotal!: number;
  floatingPrecision!: number;
  exchanges!: ExchangeInfo;

  get total(): number {
    return this.fiatTotal + this.blockchainTotal;
  }

  blockchainTotals!: AssetBalance[];
  search: string = '';

  headers = [
    { text: 'Asset', value: 'asset' },
    { text: 'Amount', value: 'amount' },
    { text: 'Value', value: 'value' },
    { text: '% of net Value', value: 'percentage' }
  ];
}
</script>

<style scoped></style>
