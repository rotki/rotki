<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { BucketTraceRow, InspectedBucket } from '@/modules/history/reconciliation/schemas';
import { type BigNumber, toHumanReadable } from '@rotki/common';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import ReconciliationAccountIdentity from '@/modules/history/reconciliation/components/ReconciliationAccountIdentity.vue';
import ReconciliationAmount from '@/modules/history/reconciliation/components/ReconciliationAmount.vue';
import { traceRowStatusLabel } from '@/modules/history/reconciliation/messages';
import { bucketEventsRoute, traceRowEventRoute } from '@/modules/history/reconciliation/routes';
import { useBucketTrace } from '@/modules/history/reconciliation/use-bucket-trace';
import { amountsFor, type BucketAmounts } from '@/modules/history/reconciliation/use-reconciliation-rows';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const open = defineModel<boolean>({ required: true });

const { target } = defineProps<{
  target?: InspectedBucket;
}>();

const ROW_STATUS_TONES: Record<string, string> = {
  negative_awaiting_rebase_reconciliation: 'text-rui-warning font-medium',
  skipped_after_stop: 'text-rui-text-disabled',
  stop: 'text-rui-error font-medium',
};

const { t } = useI18n({ useScope: 'global' });

const { matchChain } = useSupportedChains();
const { getBaseCounterpartyData } = useHistoryEventCounterpartyMappings();
const {
  earlierCount,
  error,
  hasEarlier,
  hasMore,
  loadEarlier,
  loading,
  loadingEarlier,
  loadingMore,
  loadMore,
  loadMoreError,
  retryInitial,
  retryPage,
  rows,
  shownFrom,
  shownTo,
  trace,
} = useBucketTrace(open, () => target);

const amounts = computed<BucketAmounts>(() =>
  target ? amountsFor(target.bucket) : { comparedAt: null, delta: null, derived: null, observed: null, observedAt: null });

/** Signed observed minus derived difference, computed even while a bucket awaits re-checking. */
const effectiveDelta = computed<BigNumber | null>(() => {
  const current = get(amounts);
  if (current.delta !== null)
    return current.delta;
  return current.derived !== null && current.observed !== null
    ? current.observed.minus(current.derived)
    : null;
});

const deltaToneClass = computed<string>(() =>
  target?.bucket.status === 'mismatch' ? 'text-rui-error' : 'text-rui-warning');

const protocolLabel = computed<string | undefined>(() => {
  const protocol = target?.bucket.protocol;
  if (!protocol)
    return undefined;
  return getBaseCounterpartyData(protocol)?.label ?? toHumanReadable(protocol, 'capitalize');
});

const showRows = computed<boolean>(() => !get(loading) && get(error) === undefined && get(rows).length > 0);

const loadMoreLabel = computed<string>(() => {
  const current = get(trace);
  if (!current)
    return '';
  if (get(hasEarlier)) {
    return t('data_issues.reconciliation.trace.load_more_range', {
      from: get(shownFrom),
      to: get(shownTo),
      total: current.pagination.total,
    });
  }
  return t('data_issues.reconciliation.trace.load_more', {
    shown: get(rows).length,
    total: current.pagination.total,
  });
});

function close(): void {
  set(open, false);
}

function eventsRouteFor(item: InspectedBucket): RouteLocationRaw {
  return bucketEventsRoute({
    asset: item.bucket.asset,
    isChainAccount: matchChain(item.account.location) !== undefined,
    location: item.account.location,
    locationLabel: item.account.locationLabel,
  });
}

function eventTypeLabel(row: BucketTraceRow): string {
  const main = toHumanReadable(row.eventType, 'capitalize');
  return row.eventSubtype && row.eventSubtype !== 'none'
    ? `${main} · ${toHumanReadable(row.eventSubtype, 'capitalize')}`
    : main;
}
</script>

<template>
  <RuiNavigationDrawer
    v-model="open"
    below-app-bar
    width="640px"
    temporary
    position="right"
    class="flex flex-col"
    :class-names="{ content: 'flex flex-col overflow-hidden' }"
    data-testid="bucket-trace-drawer"
  >
    <div
      v-if="target"
      class="flex items-start justify-between gap-3 px-5 py-4 border-b border-default shrink-0"
    >
      <div class="flex flex-col gap-1 min-w-0">
        <div class="text-xs font-medium uppercase tracking-wide text-rui-text-secondary">
          {{ t('data_issues.reconciliation.trace.title') }}
        </div>
        <AssetDetails :asset="target.bucket.asset" />
        <div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-rui-text-secondary">
          <ReconciliationAccountIdentity
            compact
            :location="target.account.location"
            :location-label="target.account.locationLabel"
          />
          <template v-if="target.bucket.protocol && protocolLabel">
            <span class="size-1 rounded-full bg-rui-text-disabled" />
            <CounterpartyDisplay
              :counterparty="target.bucket.protocol"
              size="14px"
              icon
            />
            <span>{{ protocolLabel }}</span>
          </template>
        </div>
      </div>
      <RuiButton
        icon
        variant="text"
        size="sm"
        :aria-label="t('common.actions.close')"
        data-testid="bucket-trace-close"
        @click="close()"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </div>

    <div
      v-if="target"
      class="flex flex-col gap-4 p-5 overflow-y-auto grow"
    >
      <div
        class="grid grid-cols-3 gap-3 rounded-rui-card border border-default bg-rui-grey-50 dark:bg-white/[0.03] p-3 text-xs"
        data-testid="bucket-trace-summary"
      >
        <div class="flex flex-col gap-0.5">
          <span class="text-rui-text-secondary">{{ t('data_issues.reconciliation.table.from_history') }}</span>
          <ReconciliationAmount
            class="text-sm font-medium"
            :amount="amounts.derived"
            :asset="target.bucket.asset"
          />
        </div>
        <div class="flex flex-col gap-0.5">
          <span class="text-rui-text-secondary">{{ t('data_issues.reconciliation.table.on_chain') }}</span>
          <ReconciliationAmount
            class="text-sm font-medium"
            :amount="amounts.observed"
            :asset="target.bucket.asset"
          />
        </div>
        <div class="flex flex-col gap-0.5">
          <span class="text-rui-text-secondary">{{ t('data_issues.reconciliation.table.difference') }}</span>
          <ReconciliationAmount
            v-if="effectiveDelta !== null && !effectiveDelta.isZero()"
            class="text-sm font-medium"
            :class="deltaToneClass"
            :amount="effectiveDelta"
            :asset="target.bucket.asset"
            signed
          />
          <span
            v-else
            class="text-sm text-rui-text-disabled"
          >
            {{ t('data_issues.reconciliation.no_value') }}
          </span>
        </div>

        <div class="col-span-3 flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-default text-rui-text-secondary">
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span v-if="target.account.historySyncedTo !== null">
              {{ t('data_issues.reconciliation.trace.last_synced') }}:
              <TimeAgoDisplay :timestamp="target.account.historySyncedTo" />
            </span>
            <span v-if="target.bucket.observedAt !== null">
              {{ t('data_issues.reconciliation.trace.observed_at') }}:
              <TimeAgoDisplay :timestamp="target.bucket.observedAt" />
            </span>
            <span v-if="trace">
              {{ t('data_issues.reconciliation.trace.effects_count', { count: trace.summary.effectsTotal }, trace.summary.effectsTotal) }}
            </span>
          </div>
          <RouterLink
            :to="eventsRouteFor(target)"
            data-testid="bucket-trace-view-events"
            @click="close()"
          >
            <RuiButton
              size="sm"
              variant="text"
              color="primary"
              tabindex="-1"
            >
              {{ t('data_issues.reconciliation.action.view_events') }}
            </RuiButton>
          </RouterLink>
        </div>
      </div>

      <RuiAlert
        v-if="trace?.summary.rebasingAsset"
        type="info"
        data-testid="bucket-trace-rebasing-note"
      >
        {{ t('data_issues.reconciliation.trace.rebasing_note') }}
      </RuiAlert>

      <RuiProgress
        v-if="loading"
        variant="indeterminate"
        color="primary"
        data-testid="bucket-trace-loading"
      />

      <FailureStrip
        v-else-if="error !== undefined"
        :title="t('data_issues.reconciliation.trace.error')"
        :failure="error"
        data-testid="bucket-trace-error"
        @retry="retryInitial()"
      />

      <div
        v-else-if="rows.length === 0"
        class="py-6 text-center text-sm text-rui-text-secondary"
        data-testid="bucket-trace-empty"
      >
        {{ t('data_issues.reconciliation.trace.empty') }}
      </div>

      <RuiButton
        v-if="showRows && hasEarlier"
        variant="outlined"
        color="primary"
        size="sm"
        :loading="loadingEarlier"
        data-testid="bucket-trace-load-earlier"
        @click="loadEarlier()"
      >
        {{ t('data_issues.reconciliation.trace.load_earlier', { count: earlierCount }) }}
      </RuiButton>

      <div
        v-if="showRows"
        class="flex flex-col divide-y divide-default rounded-rui-card border border-default"
        data-testid="bucket-trace-rows"
      >
        <div
          v-for="(row, index) in rows"
          :key="`${row.eventIdentifier ?? 'none'}-${row.sequenceIndex}-${index}`"
          class="flex flex-col gap-1 px-3 py-2.5 text-xs"
          :class="{ 'bg-rui-error/5': row.status === 'stop', 'opacity-60': row.status === 'skipped_after_stop' }"
          data-testid="bucket-trace-row"
        >
          <div class="flex flex-wrap items-center gap-2">
            <DateDisplay
              class="text-rui-text-secondary shrink-0"
              :timestamp="row.timestampMs"
              milliseconds
            />
            <span class="font-medium text-rui-text truncate">{{ eventTypeLabel(row) }}</span>
            <CounterpartyDisplay
              v-if="row.counterparty"
              :counterparty="row.counterparty"
              size="14px"
              icon
            />
            <ReconciliationAmount
              class="ml-auto font-medium shrink-0"
              :class="row.direction === 'in' ? 'text-rui-success' : 'text-rui-error'"
              :amount="row.signedAmount"
              :asset="target.bucket.asset"
              signed
            />
            <RouterLink
              v-if="row.groupIdentifier"
              :to="traceRowEventRoute(row.groupIdentifier, row.eventAsset)"
              :aria-label="t('data_issues.reconciliation.action.view_event')"
              data-testid="bucket-trace-row-link"
              @click="close()"
            >
              <RuiIcon
                name="lu-external-link"
                size="12"
                class="text-rui-primary"
              />
            </RouterLink>
          </div>
          <div class="flex flex-wrap items-center gap-1.5 text-rui-text-secondary tabular-nums">
            <ReconciliationAmount
              :amount="row.balanceBefore"
              :asset="target.bucket.asset"
            />
            <RuiIcon
              name="lu-arrow-right"
              size="12"
            />
            <ReconciliationAmount
              class="font-medium text-rui-text"
              :amount="row.balanceAfter"
              :asset="target.bucket.asset"
            />
            <span
              class="ml-auto"
              :class="ROW_STATUS_TONES[row.status] ?? 'text-rui-text-secondary'"
              data-testid="bucket-trace-row-status"
            >
              {{ t(traceRowStatusLabel(row.status)) }}
            </span>
          </div>
        </div>
      </div>

      <FailureStrip
        v-if="showRows && loadMoreError !== undefined"
        :title="t('data_issues.reconciliation.trace.load_more_error')"
        :failure="loadMoreError"
        data-testid="bucket-trace-load-more-error"
        @retry="retryPage()"
      />

      <RuiButton
        v-if="showRows && hasMore && trace"
        variant="outlined"
        color="primary"
        size="sm"
        :loading="loadingMore"
        data-testid="bucket-trace-load-more"
        @click="loadMore()"
      >
        {{ loadMoreLabel }}
      </RuiButton>
    </div>
  </RuiNavigationDrawer>
</template>
