<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { HistoricalBalanceStop } from '@/modules/history/balances/types';
import { OverlayMode } from '@/modules/history/balances/use-accounting-overlay';

const { stop, asset, eventIdentifier } = defineProps<{
  stop: HistoricalBalanceStop;
  asset: string;
  /** The event of the row, which is the stopping event itself when the stop starts here. */
  eventIdentifier: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const isStoppingEvent = computed<boolean>(() => stop.eventIdentifier === eventIdentifier);

/**
 * Where the user can resolve the stop: its data issue, else the stopping event itself.
 *
 * @remarks
 * The events view pages to an event only through its group, so a stop with neither an issue nor
 * a surviving event gets no link rather than one that lands on an unfiltered list. The stopping
 * event's own row gets no event link either, since it would only point back at itself. The event
 * link keeps the overlay on, so the user lands on the column they came from.
 */
const route = computed<RouteLocationRaw | undefined>(() => {
  if (stop.issueId !== null) {
    return {
      name: '/history/data-issues/[[tab]]',
      params: { tab: 'issues' },
      query: { issue: String(stop.issueId) },
    };
  }
  if (stop.groupIdentifier === null || get(isStoppingEvent))
    return undefined;

  return {
    name: '/history/events/',
    query: {
      asset,
      highlightedNegativeBalanceEvent: String(stop.eventIdentifier),
      overlay: OverlayMode.BALANCE,
      targetGroupIdentifier: stop.groupIdentifier,
    },
  };
});

const explanation = computed<string>(() => {
  if (get(isStoppingEvent)) {
    return stop.issueId === null
      ? t('accounting_overlay.blocked.self_no_link')
      : t('accounting_overlay.blocked.self_open_issue');
  }
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
            class="text-rui-warning shrink-0 m-0.5"
          />
        </RouterLink>
        <RuiIcon
          v-else
          name="lu-triangle-alert"
          size="14"
          class="text-rui-warning cursor-help shrink-0 m-0.5"
        />
      </template>
      {{ explanation }}
    </RuiTooltip>
  </div>
</template>
