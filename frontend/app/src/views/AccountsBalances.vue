<template>
  <v-container class="accounts-balances">
    <base-page-header :text="$t('accounts_balances.title')" />
    <tab-navigation :tab-contents="accountsBalancesTabs" />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';

@Component({
  components: {
    BasePageHeader,
    TabNavigation
  }
})
export default class AccountsBalances extends Vue {
  readonly accountsBalancesTabs: TabContent[] = [
    {
      name: 'Blockchain Balances',
      routeTo: '/accounts-balances/blockchain-balances'
    },
    {
      name: 'Exchange Balances',
      routeTo: '/accounts-balances/exchange-balances/'
    },
    {
      name: 'Manual Balances',
      routeTo: '/accounts-balances/manual-balances'
    }
  ];
}
</script>
