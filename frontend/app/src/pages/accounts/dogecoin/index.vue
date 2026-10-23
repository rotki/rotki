<script setup lang="ts">
import { msg } from '@/message-key';
import AccountBalancesDefaultPage from '@/modules/accounts/AccountBalancesDefaultPage.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.accounts_sub.dogecoin'), icon: 'lu-dog', parent: '/accounts/', order: 50, drawer: 'accounts-dogecoin' },
  },
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <AccountBalancesDefaultPage
    category="dogecoin"
    :title="t('navigation_menu.accounts_sub.dogecoin')"
    :add-label="t('blockchain_balances.add_dogecoin_account')"
  />
</template>
