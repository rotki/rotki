<template>
  <v-container class="blockchain-accounts-balances">
    <v-row>
      <v-col>
        <h1>Blockchain Accounts/Balances</h1>
      </v-col>
    </v-row>
    <blockchain-balances></blockchain-balances>
    <fiat-balances></fiat-balances>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import FiatBalances from '@/components/settings/FiatBalances.vue';
import BlockchainBalances from '@/components/settings/BlockchainBalances.vue';

@Component({
  components: {
    FiatBalances,
    BlockchainBalances
  }
})
export default class BlockchainAccountsBalances extends Vue {}
</script>

<style scoped></style>
