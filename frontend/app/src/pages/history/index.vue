<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { useAppRoutes } from '@/router/routes';
import { type TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [
    Routes.HISTORY_TRADES,
    Routes.HISTORY_DEPOSITS_WITHDRAWALS,
    Routes.HISTORY_EVENTS,
    Routes.HISTORY_LEDGER_ACTIONS
  ];
});

const { dark } = useTheme();
</script>

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
