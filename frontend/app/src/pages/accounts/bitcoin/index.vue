<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
import AccountBalancesDefaultPage from '@/components/accounts/AccountBalancesDefaultPage.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.ACCOUNTS_BITCOIN,
  },
  name: 'accounts-bitcoin',
});

const { t } = useI18n();
</script>

<template>
  <AccountBalancesDefaultPage
    category="bitcoin"
    :title="t('navigation_menu.accounts_sub.bitcoin')"
  />
</template>
