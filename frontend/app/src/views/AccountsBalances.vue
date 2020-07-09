<template>
  <v-container class="accounts-balances">
    <base-page-header text="Accounts & Balances"></base-page-header>
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
import BasePageHeader from '@/components/base/BasePageHeader.vue';

@Component({
  components: {
    ManualBalances,
    BasePageHeader,
    FiatBalances,
    BlockchainBalances
  }
})
export default class AccountsBalances extends Vue {}
</script>

<style scoped></style>
