<template>
  <v-container>
    <base-page-header :text="$t('history.header')" />
    <tab-navigation :tab-contents="tabs" />
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
export default class History extends Vue {
  readonly tabs: TabContent[] = [
    {
      name: this.$tc('history.tabs.trades'),
      routeTo: '/history/trades'
    },
    {
      name: this.$tc('history.tabs.deposits_withdrawals'),
      routeTo: '/history/deposits-withdrawals'
    }
  ];
}
</script>
