<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Deposits & Withdrawals
          </v-card-title>
          <v-card-text>
            <v-data-table :headers="headers"></v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class DepositsWithdrawals extends Vue {
  headers = [
    { text: 'Location', value: 'location' },
    { text: 'Action', value: 'movementCategory' },
    { text: 'Asset', value: 'asset', align: 'end' },
    { text: 'Amount', value: 'amount', align: 'end' },
    { text: 'USD Value', value: 'usdValue', align: 'end' },
    { text: 'Fee', value: 'fee', align: 'end' },
    { text: 'Fee Currency', value: 'feeCurrency', align: 'end' }
  ];
}
</script>

<style scoped></style>
