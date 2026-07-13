<script setup lang="ts">
import { msg } from '@/message-key';
import ManageCounterpartyMapping from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMapping.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_assets_sub.counterparty_mapping'), icon: 'lu-list-todo', parent: '/asset-manager/' },
  },
});
</script>

<template>
  <ManageCounterpartyMapping />
</template>
