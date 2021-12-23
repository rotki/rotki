<template>
  <tab-navigation :tab-contents="tabs" data-cy="accounts-balances-tab" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';

const tabs: TabContent[] = [
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
  },
  {
    name: i18n.t('account_balances.tabs.nonfungible').toString(),
    routeTo: Routes.NON_FUNGIBLE
  }
];

export default defineComponent({
  components: {
    TabNavigation
  },
  setup() {
    return { tabs };
  }
});
</script>
