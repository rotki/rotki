<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { HistoricalBalanceStop } from '@/modules/history/balances/types';

const { stop, asset } = defineProps<{
  stop: HistoricalBalanceStop;
  asset: string;
}>();

const { t } = useI18n({ useScope: 'global' });

/**
 * Where the user can resolve the stop: its data issue, else the stopping event itself.
 *
 * @remarks
 * The events view pages to an event only through its group, so a stop with neither an issue nor
 * a surviving event gets no link rather than one that lands on an unfiltered list.
 */
const route = computed<RouteLocationRaw | undefined>(() => {
  if (stop.issueId !== null) {
    return {
      name: '/history/data-issues/[[tab]]',
      params: { tab: 'issues' },
      query: { issue: String(stop.issueId) },
    };
  }
  if (stop.groupIdentifier === null)
    return undefined;

  return {
    name: '/history/events/',
    query: {
      asset,
      highlightedNegativeBalanceEvent: String(stop.eventIdentifier),
      targetGroupIdentifier: stop.groupIdentifier,
    },
  };
});

const explanation = computed<string>(() => {
  if (stop.issueId !== null)
    return t('accounting_overlay.blocked.open_issue');
  if (stop.groupIdentifier !== null)
    return t('accounting_overlay.blocked.view_event');
  return t('accounting_overlay.blocked.no_link');
});
</script>

<template>
  <div
    class="flex items-center justify-end gap-1.5"
    data-testid="accounting-overlay-blocked"
  >
    <span class="text-rui-text-disabled">{{ t('accounting_overlay.no_data') }}</span>
    <RuiTooltip
      :open-delay="200"
      :options="{ placement: 'left' }"
    >
      <template #activator>
        <RouterLink
          v-if="route"
          :to="route"
          :aria-label="explanation"
          class="flex"
          data-testid="accounting-overlay-blocked-link"
        >
          <RuiIcon
            name="lu-triangle-alert"
            size="14"
            class="text-rui-warning shrink-0"
          />
        </RouterLink>
        <RuiIcon
          v-else
          name="lu-triangle-alert"
          size="14"
          class="text-rui-warning cursor-help shrink-0"
        />
      </template>
      {{ explanation }}
    </RuiTooltip>
  </div>
</template>
