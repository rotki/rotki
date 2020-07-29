<template>
  <v-container>
    <base-page-header text="Trades"></base-page-header>
    <tab-navigation :tab-contents="tabs"></tab-navigation>
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
      name: 'Trades',
      routeTo: '/trades/trade-history'
    },
    {
      name: 'Deposits & Withdrawals',
      routeTo: '/trades/deposits-withdrawals'
    }
  ];
}
</script>

<style scoped></style>
