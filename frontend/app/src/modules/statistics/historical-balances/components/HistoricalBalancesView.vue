<script setup lang="ts">
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import HistoricalBalancesAsOf from '@/modules/statistics/historical-balances/components/HistoricalBalancesAsOf.vue';
import HistoricalBalancesFilters from '@/modules/statistics/historical-balances/components/HistoricalBalancesFilters.vue';
import HistoricalBalancesTable from '@/modules/statistics/historical-balances/components/HistoricalBalancesTable.vue';
import { useAsOfDate } from '@/modules/statistics/historical-balances/use-as-of-date';
import { useHistoricalBalanceValues } from '@/modules/statistics/historical-balances/use-historical-balance-values';
import { useHistoricalBalancesAt } from '@/modules/statistics/historical-balances/use-historical-balances-at';
import { useHistoricalBalancesExport } from '@/modules/statistics/historical-balances/use-historical-balances-export';
import { ProcessingState, useHistoricalBalancesProcessing } from '@/modules/statistics/historical-balances/use-historical-balances-processing';
import { useHistoricalBalancesView } from '@/modules/statistics/historical-balances/use-historical-balances-view';

const { t } = useI18n({ useScope: 'global' });

const { modelDay, restamp, timestamp } = useAsOfDate();
const { empty, error, groups, loadedAt, loading, processingRequired, refresh } = useHistoricalBalancesAt(timestamp);
const shownAt = computed<number>(() => get(loadedAt) ?? get(timestamp));
const { rows: pricedRows } = useHistoricalBalanceValues(groups, shownAt);
const {
  accounts,
  filtered,
  locations,
  modelAccounts,
  modelLocations,
  modelMode,
  modelSearch,
  rows,
  summary,
} = useHistoricalBalancesView(pricedRows);
const { blockedReason, exportCsv } = useHistoricalBalancesExport({
  accounts: modelAccounts,
  loading,
  locations: modelLocations,
  processingRequired,
  rows,
  search: modelSearch,
  summary,
  timestamp: shownAt,
});
const { failure, processNow, state: processingState } = useHistoricalBalancesProcessing();

/** A day came back empty after events were processed, so there is nothing left to offer. */
const emptyAfterProcessing = computed<boolean>(() => !get(processingRequired) && get(processingState) === ProcessingState.DONE);

/** Today's as-of time is now, so a refresh first moves it forward; that change reloads on its own. */
async function reload(): Promise<void> {
  if (!restamp())
    await refresh();
}
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.statistics_sub.historical_balances')]">
    <template #buttons>
      <RuiTooltip
        :disabled="!blockedReason"
        :open-delay="200"
        :class-names="{ tooltip: 'max-w-[16rem]' }"
      >
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :disabled="!!blockedReason"
            data-testid="historical-balances-export"
            @click="exportCsv()"
          >
            <template #prepend>
              <RuiIcon name="lu-file-spreadsheet" />
            </template>
            {{ t('historical_balances.export.action') }}
          </RuiButton>
        </template>
        {{ blockedReason }}
      </RuiTooltip>
      <RuiButton
        variant="outlined"
        color="primary"
        :loading="loading"
        data-testid="historical-balances-refresh"
        @click="reload()"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-cw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>
    </template>

    <RuiCard content-class="flex flex-col gap-4">
      <HistoricalBalancesAsOf v-model="modelDay" />

      <RuiAlert
        v-if="processingRequired || empty"
        :type="processingRequired ? 'warning' : 'info'"
        data-testid="historical-balances-processing"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <span v-if="processingRequired">{{ t('historical_balances.processing.message') }}</span>
          <span v-else-if="emptyAfterProcessing">{{ t('historical_balances.processing.done_empty') }}</span>
          <span v-else>{{ t('historical_balances.processing.empty_message') }}</span>
          <RuiButton
            v-if="!emptyAfterProcessing"
            size="sm"
            color="primary"
            :loading="processingState === ProcessingState.RUNNING"
            data-testid="historical-balances-process"
            @click="processNow()"
          >
            {{ t('historical_balances.processing.action') }}
          </RuiButton>
        </div>
        <div
          v-if="processingState === ProcessingState.NOT_STARTED"
          class="mt-2 text-body-2"
          data-testid="historical-balances-process-not-started"
        >
          {{ t('historical_balances.processing.not_started') }}
        </div>
        <div
          v-else-if="processingState === ProcessingState.FAILED"
          class="mt-2 text-body-2"
          data-testid="historical-balances-process-failed"
        >
          {{ t('historical_balances.processing.failed', { message: failure }) }}
        </div>
      </RuiAlert>

      <RuiAlert
        v-if="error"
        type="error"
        data-testid="historical-balances-error"
      >
        {{ t('historical_balances.error', { message: error }) }}
      </RuiAlert>

      <div
        v-else-if="rows.length > 0"
        data-testid="historical-balances-total"
      >
        <div class="text-rui-text-secondary text-caption uppercase">
          <i18n-t
            keypath="historical_balances.total.title"
            scope="global"
          >
            <template #date>
              <DateDisplay
                :timestamp="shownAt"
                no-time
              />
            </template>
          </i18n-t>
          <span
            v-if="filtered"
            class="ml-1"
            data-testid="historical-balances-total-filtered"
          >
            {{ t('historical_balances.total.filtered') }}
          </span>
        </div>
        <FiatDisplay
          class="text-h5 font-medium"
          :value="summary.total"
          :loading="summary.pendingCount > 0 && summary.total.isZero()"
        />
        <div
          v-if="summary.pendingCount > 0 || summary.missingCount > 0 || summary.spamCount > 0"
          class="flex flex-col text-body-2 text-rui-text-secondary mt-1"
        >
          <span v-if="summary.pendingCount > 0">{{ t('historical_balances.total.pending', { count: summary.pendingCount }, summary.pendingCount) }}</span>
          <span v-if="summary.missingCount > 0">{{ t('historical_balances.total.missing', { count: summary.missingCount }, summary.missingCount) }}</span>
          <span
            v-if="summary.spamCount > 0"
            data-testid="historical-balances-spam-count"
          >
            {{ t('historical_balances.total.spam', { count: summary.spamCount }, summary.spamCount) }}
          </span>
        </div>
        <div
          class="text-caption text-rui-text-secondary mt-1"
          data-testid="historical-balances-coverage"
        >
          {{ t('historical_balances.total.coverage') }}
        </div>
      </div>

      <template v-if="!error">
        <HistoricalBalancesFilters
          v-model:locations="modelLocations"
          v-model:accounts="modelAccounts"
          v-model:search="modelSearch"
          v-model:mode="modelMode"
          :location-options="locations"
          :account-options="accounts"
        />
        <HistoricalBalancesTable
          :rows="rows"
          :loading="loading"
          :filtered="filtered"
        />
      </template>
    </RuiCard>
  </TablePageLayout>
</template>
