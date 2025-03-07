<script setup lang="ts">
import AccountBalancesDefaultPage from '@/components/accounts/AccountBalancesDefaultPage.vue';
import { NoteLocation } from '@/types/notes';

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
