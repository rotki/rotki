<template>
  <tab-navigation :tab-contents="tabs" class="decentralized-deposits" />
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { Routes } from '@/router/routes';

@Component({
  components: { TabNavigation }
})
export default class DecentralizedDeposits extends Vue {
  readonly tabs: TabContent[] = [
    {
      name: this.$tc('decentralized_deposits.protocols'),
      routeTo: Routes.DEFI_DEPOSITS_PROTOCOLS
    },
    {
      name: this.$tc('decentralized_deposits.liquidity'),
      routeTo: Routes.DEFI_DEPOSITS_LIQUIDITY
    }
  ];
}
</script>
