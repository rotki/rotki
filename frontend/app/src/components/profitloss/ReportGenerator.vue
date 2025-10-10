<script setup lang="ts">
import type { ProfitLossReportPeriod } from '@/types/reports';
import RangeSelector from '@/components/helper/date/RangeSelector.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useRefWithDebounce } from '@/composables/ref';
import {
  useHistoryQueryIndicatorSettings,
} from '@/modules/dashboard/history-events/composables/use-history-query-indicator-settings';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { Routes } from '@/router/routes';
import { useHistoryStore } from '@/store/history';

const emit = defineEmits<{
  (e: 'generate', data: ProfitLossReportPeriod): void;
  (e: 'export-data', data: ProfitLossReportPeriod): void;
  (e: 'import-data'): void;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const historyStore = useHistoryStore();
const { transactionStatusSummary } = storeToRefs(historyStore);
const { processing: rawProcessing } = useHistoryEventsStatus();
const processing = useRefWithDebounce(rawProcessing, 400);
const { minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();

const range = ref<ProfitLossReportPeriod>({ end: 0, start: 0 });
const valid = ref<boolean>(false);

const isOutOfSync = computed<boolean>(() => {
  const status = get(transactionStatusSummary);
  if (!isDefined(status)) {
    return false;
  }

  const { evmLastQueriedTs = 0, exchangesLastQueriedTs = 0, hasEvmAccounts = false, hasExchangesAccounts = false } = status;

  // Only check if user has accounts
  if (!hasEvmAccounts && !hasExchangesAccounts) {
    return false;
  }

  const now = Date.now();
  const minOutOfSyncMs = get(minOutOfSyncPeriodMs);

  // Check EVM if user has EVM accounts
  if (hasEvmAccounts && evmLastQueriedTs > 0) {
    const evmLastQueriedMs = evmLastQueriedTs * 1000;
    if (now - evmLastQueriedMs >= minOutOfSyncMs) {
      return true;
    }
  }

  // Check exchanges if user has exchange accounts
  if (hasExchangesAccounts && exchangesLastQueriedTs > 0) {
    const exchangesLastQueriedMs = exchangesLastQueriedTs * 1000;
    if (now - exchangesLastQueriedMs >= minOutOfSyncMs) {
      return true;
    }
  }

  // Also consider it out of sync if never queried
  return (hasEvmAccounts && evmLastQueriedTs === 0) || (hasExchangesAccounts && exchangesLastQueriedTs === 0);
});

const canGenerate = computed<boolean>(() => get(valid) && !get(processing) && !get(isOutOfSync));

function generate(): void {
  emit('generate', get(range));
}

function exportReportData(): void {
  emit('export-data', get(range));
}

function importReportData(): void {
  emit('import-data');
}

function navigateToHistory(): void {
  router.push('/history');
}

const accountSettingsRoute = Routes.SETTINGS_ACCOUNTING;
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex justify-between px-4 py-2">
        <CardTitle>
          {{ t('common.actions.generate') }}
        </CardTitle>
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RouterLink :to="accountSettingsRoute">
              <RuiButton
                variant="text"
                icon
                color="primary"
              >
                <RuiIcon name="lu-settings" />
              </RuiButton>
            </RouterLink>
          </template>
          <span>{{ t('profit_loss_report.settings_tooltip') }}</span>
        </RuiTooltip>
      </div>
    </template>
    <RangeSelector
      v-model="range"
      @update:valid="valid = $event"
    />
    <RuiAlert
      v-if="isOutOfSync || processing"
      type="warning"
      class="mt-6"
    >
      <template v-if="processing">
        {{ t('profit_loss_report.processing_alert') }}
      </template>
      <template v-else>
        <div class="flex flex-col items-start gap-2">
          <div>{{ t('profit_loss_report.out_of_sync_alert') }}</div>
          <RuiButton
            size="sm"
            color="primary"
            variant="outlined"
            @click="navigateToHistory()"
          >
            {{ t('profit_loss_report.go_to_history') }}
          </RuiButton>
        </div>
      </template>
    </RuiAlert>
    <template #footer>
      <div class="flex gap-4 w-full">
        <div class="grow">
          <RuiButton
            class="w-full"
            color="primary"
            size="lg"
            :disabled="!canGenerate"
            @click="generate()"
          >
            <template #prepend>
              <RuiIcon name="lu-scroll-text" />
            </template>
            {{ t('common.actions.generate') }}
          </RuiButton>
        </div>
        <div>
          <RuiMenu
            close-on-content-click
            :popper="{ placement: 'bottom-end' }"
          >
            <template #activator="{ attrs }">
              <RuiButton
                class="h-[2.625rem]"
                size="lg"
                v-bind="attrs"
              >
                <template #prepend>
                  <RuiIcon name="lu-bug" />
                </template>
                {{ t('profit_loss_reports.debug.title') }}
              </RuiButton>
            </template>
            <div class="py-2">
              <RuiButton
                variant="list"
                @click="exportReportData()"
              >
                <template #prepend>
                  <RuiIcon name="lu-file-down" />
                </template>
                {{ t('profit_loss_reports.debug.export_data') }}
              </RuiButton>
              <RuiButton
                variant="list"
                @click="importReportData()"
              >
                <template #prepend>
                  <RuiIcon name="lu-file-up" />
                </template>
                {{ t('profit_loss_reports.debug.import_data') }}
              </RuiButton>
            </div>
          </RuiMenu>
        </div>
      </div>
    </template>
  </RuiCard>
</template>
