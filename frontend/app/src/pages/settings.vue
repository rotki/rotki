<script setup lang="ts">
import { msg } from '@/message-key';
import SettingsSearch from '@/modules/settings/SettingsSearch.vue';
import TabNavigation from '@/modules/shell/components/TabNavigation.vue';
import { useNavTabs } from '@/modules/shell/layout/use-nav-tabs';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.settings'), icon: 'lu-settings', searchable: false },
  },
  redirect: { name: '/settings/account/' },
});

const { t } = useI18n({ useScope: 'global' });

const tabs = useNavTabs([
  '/settings/account/',
  '/settings/general/',
  '/settings/database/',
  '/settings/accounting/',
  '/settings/evm/',
  '/settings/oracle/',
  '/settings/rpc/',
  '/settings/modules/',
  '/settings/interface/',
]);
</script>

<template>
  <div class="container lg:px-8">
    <div class="flex flex-wrap items-center justify-between gap-x-8 gap-y-4 mb-6">
      <h5 class="text-h5 font-semibold">
        {{ t('navigation_menu.settings') }}
      </h5>

      <SettingsSearch />
    </div>
    <TabNavigation
      :tabs="tabs"
      plain
      child
      class="settings"
    />
  </div>
</template>
