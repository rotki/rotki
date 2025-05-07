<script setup lang="ts">
import AccountBalancesDefaultPage from '@/components/accounts/AccountBalancesDefaultPage.vue';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.ACCOUNTS_SUBSTRATE,
  },
  name: 'accounts-substrate',
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <AccountBalancesDefaultPage
    category="substrate"
    :title="t('navigation_menu.accounts_sub.substrate')"
  />
</template>
