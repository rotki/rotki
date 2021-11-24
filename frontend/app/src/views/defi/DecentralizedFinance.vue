<template>
  <div>
    <tab-navigation
      v-if="defiSetupDone"
      :tab-contents="tabs"
      no-content-margin
    />
    <defi-wizard v-else class="mt-8" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { mapState } from 'vuex';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import { DEFI_SETUP_DONE } from '@/types/frontend-settings';

const tabs: TabContent[] = [
  {
    name: i18n.t('decentralized_finance.tabs.overview').toString(),
    routeTo: Routes.DEFI_OVERVIEW
  },
  {
    name: i18n.t('decentralized_finance.tabs.deposits').toString(),
    routeTo: Routes.DEFI_DEPOSITS
  },
  {
    name: i18n.t('decentralized_finance.tabs.liabilities').toString(),
    routeTo: Routes.DEFI_LIABILITIES
  },
  {
    name: i18n.t('decentralized_finance.tabs.dex_trades').toString(),
    routeTo: Routes.DEFI_DEX_TRADES
  },
  {
    name: i18n.t('decentralized_finance.tabs.airdrops').toString(),
    routeTo: Routes.DEFI_AIRDROPS
  }
];

export default defineComponent({
  name: 'DecentralizedFinance',
  components: { DefiWizard, TabNavigation },
  setup() {
    return { tabs };
  },
  computed: {
    ...mapState('settings', [DEFI_SETUP_DONE])
  }
});
</script>

<style scoped lang="scss">
.decentralized-finance {
  height: 100%;
}
</style>
