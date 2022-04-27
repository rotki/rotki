<template>
  <tab-navigation :tab-contents="tabs" class="settings" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { Routes } from '@/router/routes';

const tabs: TabContent[] = [
  Routes.SETTINGS_GENERAL,
  Routes.SETTINGS_ACCOUNTING,
  Routes.SETTINGS_DATA_SECURITY,
  Routes.SETTINGS_MODULES
];

export default defineComponent({
  name: 'Settings',
  components: { TabNavigation },
  setup() {
    return { tabs };
  }
});
</script>
