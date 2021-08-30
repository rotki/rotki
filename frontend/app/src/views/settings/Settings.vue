<template>
  <tab-navigation :tab-contents="tabs" class="settings" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import i18n from '@/i18n';

const tabs: TabContent[] = [
  {
    name: i18n.t('settings.tabs.general').toString(),
    routeTo: '/settings/general'
  },
  {
    name: i18n.t('settings.tabs.accounting').toString(),
    routeTo: '/settings/accounting'
  },
  {
    name: i18n.t('settings.tabs.data_security').toString(),
    routeTo: '/settings/data-security'
  },
  {
    name: i18n.t('settings.tabs.modules').toString(),
    routeTo: '/settings/modules'
  }
];

export default defineComponent({
  name: 'Settings',
  components: { TabNavigation },
  setup() {
    return { tabs };
  }
});
</script>
