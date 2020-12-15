<template>
  <v-container class="staking">
    <base-page-header :text="$t('staking.title')" />
    <v-container class="staking__content">
      <no-premium-placeholder v-if="!premium" :text="$t('staking.title')" />
      <div v-else>
        <tab-navigation :tab-contents="stakingTabs" />
      </div>
    </v-container>
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import { Routes } from '@/router/routes';

@Component({
  components: {
    TabNavigation,
    NoPremiumPlaceholder,
    BasePageHeader
  }
})
export default class Staking extends Mixins(PremiumMixin) {
  readonly stakingTabs: TabContent[] = [
    {
      routeTo: Routes.STAKING_ETH2,
      name: `${this.$t('staking.eth2')}`
    },
    {
      routeTo: Routes.STAKING_ADEX,
      name: `${this.$t('staking.adex')}`
    }
  ];
}
</script>

<style scoped lang="scss">
.staking {
  height: 100%;

  &__content {
    height: calc(100% - 120px);
  }
}
</style>
