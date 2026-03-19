<script setup lang="ts">
import AccountBalancesDefaultPage from '@/components/accounts/AccountBalancesDefaultPage.vue';

definePage({
  name: 'accounts-starknet',
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <AccountBalancesDefaultPage
    category="starknet"
    :title="t('navigation_menu.accounts_sub.starknet')"
  />
</template>
