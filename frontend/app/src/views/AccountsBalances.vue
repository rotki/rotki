<template>
  <v-container class="accounts-balances">
    <base-page-header text="Accounts & Balances"></base-page-header>
    <tab-navigation :tab-contents="accountsBalancesTabs"></tab-navigation>
    <v-slide-x-transition>
      <router-view />
    </v-slide-x-transition>
    <!-- <blockchain-balances></blockchain-balances>
    <fiat-balances></fiat-balances>
    <manual-balances></manual-balances> -->
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
// import BlockchainBalances from '@/components/accounts/BlockchainBalances.vue';
// import FiatBalances from '@/components/accounts/FiatBalances.vue';
// import ManualBalances from '@/components/accounts/ManualBalances.vue';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import TabNavigation from '@/components/helper/TabNavigation.vue';

@Component({
  components: {
    // ManualBalances,
    BasePageHeader,
    // FiatBalances,
    // BlockchainBalances,
    TabNavigation
  }
})
export default class AccountsBalances extends Vue {
  accountsBalancesTabs = [
    {
      name: 'Blockchain Balances',
      routerTo: '/accounts-balances/blockchain-balances'
    },
    {
      name: 'Exchange Balances',
      routerTo: '/accounts-balances/exchange-balances/'
    },
    {
      name: 'Manual Balances',
      routerTo: '/accounts-balances/manual-balances'
    }
  ];
}
</script>

<style scoped></style>
