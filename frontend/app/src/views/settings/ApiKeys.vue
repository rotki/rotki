<template>
  <tab-navigation class="api-keys" :tab-contents="tabs" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import i18n from '@/i18n';

const tabs: TabContent[] = [
  {
    name: i18n.t('api_keys.tabs.premium').toString(),
    routeTo: '/settings/api-keys/rotki-premium'
  },
  {
    name: i18n.t('api_keys.tabs.exchanges').toString(),
    routeTo: '/settings/api-keys/exchanges'
  },
  {
    name: i18n.t('api_keys.tabs.external_services').toString(),
    routeTo: '/settings/api-keys/external-services'
  }
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
