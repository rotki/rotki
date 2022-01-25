<template>
  <tab-navigation :tab-contents="tabs" class="decentralized-deposits" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';

export default defineComponent({
  name: 'DecentralizedDeposits',
  components: { TabNavigation },
  setup() {
    const tabs: TabContent[] = [
      {
        name: i18n.t('decentralized_deposits.protocols').toString(),
        routeTo: Routes.DEFI_DEPOSITS_PROTOCOLS
      },
      {
        name: i18n.t('decentralized_deposits.liquidity').toString(),
        routeTo: Routes.DEFI_DEPOSITS_LIQUIDITY
      }
    ];

    return {
      tabs
    };
  }
});
</script>
