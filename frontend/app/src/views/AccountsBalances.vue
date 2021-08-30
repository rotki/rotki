<template>
  <tab-navigation :tab-contents="tabs" data-cy="accounts-balances" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';

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
