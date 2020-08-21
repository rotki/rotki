<template>
  <v-container>
    <base-page-header :text="$t('trades.header')" />
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
export default class TradesHistory extends Vue {
  readonly tabs: TabContent[] = [
    {
      name: this.$t('trades.tabs.trades').toString(),
      routeTo: '/trades/trade-history'
    },
    {
      name: this.$t('trades.tabs.deposits_withdrawals').toString(),
      routeTo: '/trades/deposits-withdrawals',
      hidden: !process.env.VUE_APP_TRADES_PREVIEW
    }
  ];
}
</script>
