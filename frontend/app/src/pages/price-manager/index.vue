<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import TabNavigation from '@/modules/shell/components/TabNavigation.vue';
import { useChildNavTabs } from '@/modules/shell/layout/use-nav-tabs';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_prices'), icon: 'lu-manage-prices', section: 2, order: 30, drawer: 'price-manager' },
    canNavigateBack: true,
    noteLocation: NoteLocation.PRICE_MANAGER,
  },
  props: true,
  redirect: '/price-manager/latest',
});

const tabs = useChildNavTabs('/price-manager/');
</script>

<template>
  <TabNavigation
    :tabs="tabs"
    child
  />
</template>
