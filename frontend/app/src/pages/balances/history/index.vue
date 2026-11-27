<script setup lang="ts">
import { definePage } from 'vue-router/experimental';
import { msg } from '@/message-key';
import AccountHistoryView from '@/modules/balances/account-history/components/AccountHistoryView.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances_sub.account_history'), icon: 'lu-chart-line', parent: '/balances/', order: 50, drawer: 'balances-history' },
  },
});
</script>

<template>
  <AccountHistoryView />
</template>
