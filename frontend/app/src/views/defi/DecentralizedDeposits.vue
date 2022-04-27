<template>
  <tab-navigation :tab-contents="tabs" class="decentralized-deposits" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { Routes } from '@/router/routes';

export default defineComponent({
  name: 'DecentralizedDeposits',
  components: { TabNavigation },
  setup() {
    const tabs: TabContent[] = [
      Routes.DEFI_DEPOSITS_PROTOCOLS,
      Routes.DEFI_DEPOSITS_LIQUIDITY
    ];

    return {
      tabs
    };
  }
});
</script>
