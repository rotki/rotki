<template>
  <div class="staking__content">
    <no-premium-placeholder v-if="!premium" :text="$t('staking.title')" />
    <tab-navigation v-else :tab-contents="tabs" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import i18n from '@/i18n';
import PremiumMixin from '@/mixins/premium-mixin';
import { Routes } from '@/router/routes';

const tabs: TabContent[] = [
  {
    routeTo: Routes.STAKING_ETH2,
    name: i18n.t('staking.eth2').toString()
  },
  {
    routeTo: Routes.STAKING_ADEX,
    name: i18n.t('staking.adex').toString()
  }
];

export default defineComponent({
  components: {
    TabNavigation,
    NoPremiumPlaceholder
  },
  mixins: [PremiumMixin],
  setup() {
    return { tabs };
  }
});
</script>

<style scoped lang="scss">
.staking {
  height: 100%;

  &__content {
    height: calc(100% - 120px);
  }
}
</style>
