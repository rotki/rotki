<template>
  <tab-navigation class="api-keys" :tab-contents="tabs" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { Routes } from '@/router/routes';

const tabs: TabContent[] = [
  Routes.API_KEYS_ROTKI_PREMIUM,
  Routes.API_KEYS_EXCHANGES,
  Routes.API_KEYS_EXTERNAL_SERVICES
];

export default defineComponent({
  name: 'ApiKeys',
  components: {
    TabNavigation
  },
  setup() {
    return { tabs };
  }
});
</script>
