<script setup lang="ts">
import ManageCounterpartyMapping from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMapping.vue';

definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.manage_assets_sub.counterparty_mapping', icon: 'lu-list-todo', parent: '/asset-manager/' },
  },
});
</script>

<template>
  <ManageCounterpartyMapping />
</template>
