<template>
  <tab-navigation :tab-contents="tabs" data-cy="accounts-balances-tab" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { Routes } from '@/router/routes';

const tabs: TabContent[] = [
  Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
  Routes.ACCOUNTS_BALANCES_EXCHANGE,
  Routes.ACCOUNTS_BALANCES_MANUAL,
  Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE
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
