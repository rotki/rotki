<template>
  <v-container>
    <v-row>
      <v-col>
        <h1 class="page-header">Dashboard</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <exchange-box
          v-for="exchange in exchanges"
          :key="exchange.name"
          :name="exchange.name"
          :amount="exchange.total"
        ></exchange-box>
        <information-box
          v-if="false"
          id="blockchain_box"
          icon="fa-hdd-o"
          :amount="0"
        ></information-box>
        <information-box
          v-if="false"
          id="banks_box"
          icon="fa-university"
          :amount="0"
        ></information-box>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <h1 class="page-header">All Balances</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
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
      </v-col>
    </v-row>
    <v-row>
      <div id="dashboard-wrapper">
        <div class="row">
          <div id="dashboard-contents" class="col-lg-12"></div>
        </div>
      </div>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import InformationBox from '@/components/InformationBox.vue';
import { mapGetters } from 'vuex';
import { ExchangeInfo } from '@/typing/types';
import { AssetBalance } from '@/model/asset-balance';
import ExchangeBox from '@/components/dashboard/ExchangeBox.vue';

@Component({
  components: { ExchangeBox, InformationBox },
  computed: {
    ...mapGetters(['floatingPrecision', 'balances/exchanges'])
  }
})
export default class Dashboard extends Vue {
  fiatTotal!: number;
  floatingPrecision!: number;
  exchanges!: ExchangeInfo;

  blockchainTotals: AssetBalance[] = [];
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
