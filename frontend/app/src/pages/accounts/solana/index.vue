<script setup lang="ts">
import AccountBalancesDefaultPage from '@/modules/accounts/AccountBalancesDefaultPage.vue';

definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.accounts_sub.solana', icon: 'lu-solana-accounts-fill', parent: '/accounts/', order: 30, drawer: 'accounts-solana' },
  },
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <AccountBalancesDefaultPage
    category="solana"
    :title="t('navigation_menu.accounts_sub.solana')"
  />
</template>
