<script setup lang="ts">
import { msg } from '@/message-key';
import AccountBalancesDefaultPage from '@/modules/accounts/AccountBalancesDefaultPage.vue';
import { NoteLocation } from '@/modules/core/common/notes';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.accounts_sub.substrate'), icon: 'lu-substrate-accounts', parent: '/accounts/', order: 40, drawer: 'accounts-substrate' },
    noteLocation: NoteLocation.ACCOUNTS_SUBSTRATE,
  },
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <AccountBalancesDefaultPage
    category="substrate"
    :title="t('navigation_menu.accounts_sub.substrate')"
  />
</template>
