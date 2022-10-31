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

<script setup lang="ts">
import { ComputedRef } from 'vue';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { useTheme } from '@/composables/common';
import { useAppRoutes } from '@/router/routes';
import { TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [
    Routes.HISTORY_TRADES,
    Routes.HISTORY_DEPOSITS_WITHDRAWALS,
    Routes.HISTORY_TRANSACTIONS,
    Routes.HISTORY_LEDGER_ACTIONS
  ];
});

const { dark } = useTheme();
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
