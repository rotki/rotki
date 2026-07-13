<script setup lang="ts">
import { msg } from '@/message-key';
import AccountBalancesDefaultPage from '@/modules/accounts/AccountBalancesDefaultPage.vue';
import { NoteLocation } from '@/modules/core/common/notes';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.accounts_sub.bitcoin'), icon: 'lu-bitcoin-accounts', parent: '/accounts/', order: 20, drawer: 'accounts-bitcoin' },
    noteLocation: NoteLocation.ACCOUNTS_BITCOIN,
  },
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <AccountBalancesDefaultPage
    category="bitcoin"
    :title="t('navigation_menu.accounts_sub.bitcoin')"
  />
</template>
