<script setup lang="ts">
import AccountBalancesDefaultPage from '@/modules/accounts/AccountBalancesDefaultPage.vue';

definePage({
  name: 'accounts-solana',
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <AccountBalancesDefaultPage
    category="solana"
    :title="t('navigation_menu.accounts_sub.solana')"
  />
</template>
