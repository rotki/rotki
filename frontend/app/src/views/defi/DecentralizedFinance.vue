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
import { Routes } from '@/router/routes';
import { DEFI_SETUP_DONE } from '@/types/frontend-settings';

const tabs: TabContent[] = [
  Routes.DEFI_OVERVIEW,
  Routes.DEFI_DEPOSITS,
  Routes.DEFI_LIABILITIES,
  Routes.DEFI_DEX_TRADES,
  Routes.DEFI_AIRDROPS
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
