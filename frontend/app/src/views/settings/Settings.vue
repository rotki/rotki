<template>
  <v-container class="settings">
    <base-page-header :text="$t('settings.title')" />
    <tab-navigation :tab-contents="settingsTabs" />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';

@Component({
  components: { BasePageHeader, TabNavigation }
})
export default class Settings extends Vue {
  readonly settingsTabs: TabContent[] = [
    {
      name: this.$t('settings.tabs.general').toString(),
      routeTo: '/settings/general'
    },
    {
      name: this.$t('settings.tabs.accounting').toString(),
      routeTo: '/settings/accounting'
    },
    {
      name: this.$t('settings.tabs.data_security').toString(),
      routeTo: '/settings/data-security'
    },
    {
      name: this.$t('settings.tabs.modules').toString(),
      routeTo: '/settings/modules'
    }
  ];
}
</script>

<style scoped lang="scss"></style>
