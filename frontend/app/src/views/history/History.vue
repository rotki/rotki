<template>
  <div
    :class="{
      [$style.history]: true,
      [$style['history--dark']]: dark
    }"
  >
    <tab-navigation :tab-contents="tabs" data-cy="history-tab" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { setupThemeCheck } from '@/composables/common';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';

const tabs: TabContent[] = [
  {
    name: i18n.t('history.tabs.trades').toString(),
    routeTo: Routes.HISTORY_TRADES
  },
  {
    name: i18n.t('history.tabs.deposits_withdrawals').toString(),
    routeTo: Routes.HISTORY_DEPOSITS_WITHDRAWALS
  },
  {
    name: i18n.t('history.tabs.transactions').toString(),
    routeTo: Routes.HISTORY_TRANSACTIONS
  },
  {
    name: i18n.t('history.tabs.ledger_actions').toString(),
    routeTo: Routes.HISTORY_LEDGER_ACTIONS
  }
];

export default defineComponent({
  name: 'History',
  components: { TabNavigation },
  setup() {
    const { dark } = setupThemeCheck();
    return { dark, tabs };
  }
});
</script>

<style module lang="scss">
.history {
  :global {
    .darken-row {
      background: #eeeeee;
    }
  }

  &--dark {
    :global {
      .darken-row {
        background: #616161;
      }
    }
  }
}
</style>
