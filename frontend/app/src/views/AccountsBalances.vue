<template>
  <v-container class="accounts-balances">
    <v-row>
      <v-col>
        <h1>Accounts & Balances</h1>
      </v-col>
    </v-row>
    <blockchain-balances></blockchain-balances>
    <fiat-balances></fiat-balances>
    <manual-balances></manual-balances>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import BlockchainBalances from '@/components/accounts/BlockchainBalances.vue';
import FiatBalances from '@/components/accounts/FiatBalances.vue';
import ManualBalances from '@/components/accounts/ManualBalances.vue';

@Component({
  components: {
    ManualBalances,
    FiatBalances,
    BlockchainBalances
  }
})
export default class AccountsBalances extends Vue {}
</script>

<style scoped></style>
