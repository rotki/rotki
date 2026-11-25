<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { HistoricalBalanceStop } from '@/modules/history/balances/types';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { msg } from '@/message-key';
import { OverlayMode } from '@/modules/history/balances/use-accounting-overlay';
import { IssueKind } from '@/modules/history/data-issues/constants';

const { stop, asset, eventIdentifier } = defineProps<{
  stop: HistoricalBalanceStop;
  asset: string;
  /** The event of the row, which is the stopping event itself when the stop starts here. */
  eventIdentifier: number;
}>();

const INVALID_EVENT_AMOUNT_KEYS = {
  noLink: msg.$t('accounting_overlay.blocked.invalid_event_amount.no_link'),
  openIssue: msg.$t('accounting_overlay.blocked.invalid_event_amount.open_issue'),
  selfNoLink: msg.$t('accounting_overlay.blocked.invalid_event_amount.self_no_link'),
  selfOpenIssue: msg.$t('accounting_overlay.blocked.invalid_event_amount.self_open_issue'),
  viewEvent: msg.$t('accounting_overlay.blocked.invalid_event_amount.view_event'),
} as const;

const NEGATIVE_BALANCE_KEYS = {
  noLink: msg.$t('accounting_overlay.blocked.no_link'),
  openIssue: msg.$t('accounting_overlay.blocked.open_issue'),
  selfNoLink: msg.$t('accounting_overlay.blocked.self_no_link'),
  selfOpenIssue: msg.$t('accounting_overlay.blocked.self_open_issue'),
  viewEvent: msg.$t('accounting_overlay.blocked.view_event'),
} as const;

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
  const keys = stop.issueKind === IssueKind.INVALID_EVENT_AMOUNT
    ? INVALID_EVENT_AMOUNT_KEYS
    : NEGATIVE_BALANCE_KEYS;
  if (get(isStoppingEvent))
    return t(stop.issueId === null ? keys.selfNoLink : keys.selfOpenIssue);
  if (stop.issueId !== null)
    return t(keys.openIssue);
  if (stop.groupIdentifier !== null)
    return t(keys.viewEvent);
  return t(keys.noLink);
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
