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
import { Routes } from '@/router/routes';

const tabs: TabContent[] = [
  Routes.HISTORY_TRADES,
  Routes.HISTORY_DEPOSITS_WITHDRAWALS,
  Routes.HISTORY_TRANSACTIONS,
  Routes.HISTORY_LEDGER_ACTIONS
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
