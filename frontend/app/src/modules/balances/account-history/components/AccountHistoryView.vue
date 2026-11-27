<script setup lang="ts">
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { AccountHistoryRange } from '@/modules/balances/account-history/account-history-selection';
import AccountHistoryEvents from '@/modules/balances/account-history/components/AccountHistoryEvents.vue';
import AccountHistorySelectors from '@/modules/balances/account-history/components/AccountHistorySelectors.vue';
import AccountHistorySummary from '@/modules/balances/account-history/components/AccountHistorySummary.vue';
import AccountBalanceChart from '@/modules/balances/account-history/components/chart/AccountBalanceChart.vue';
import { useAccountHistory } from '@/modules/balances/account-history/use-account-history';
import GetPremiumPlaceholder from '@/modules/shell/components/GetPremiumPlaceholder.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const {
  assets,
  assetsLoading,
  assetsProcessingRequired,
  buckets,
  empty,
  error,
  eventsRange,
  loading,
  locations,
  modelAccount,
  modelAsset,
  modelLocation,
  modelRange,
  picked,
  premium,
  processingRequired,
  refresh,
  selection,
  summary,
  total,
} = useAccountHistory();

/**
 * What the chart card shows instead of the chart. The card keeps its place and size for every one
 * of them, so picking, an empty range or a failed load never moves the page.
 */
const placeholder = computed<'premium' | 'error' | 'pick' | 'empty' | undefined>(() => {
  if (!get(premium))
    return 'premium';
  if (get(error))
    return 'error';
  if (!get(picked))
    return 'pick';
  return get(empty) ? 'empty' : undefined;
});

/** A bounded range waits for its window, so the list does not first fetch all time. */
const showEvents = computed<boolean>(() =>
  get(picked) && (get(selection).range === AccountHistoryRange.ALL || !!get(eventsRange)),
);
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.balances'), t('navigation_menu.balances_sub.account_history')]">
    <template #buttons>
      <RuiButton
        variant="outlined"
        color="primary"
        :loading="loading"
        :disabled="!premium || !picked"
        data-testid="account-history-refresh"
        @click="refresh()"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-cw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>
    </template>

    <div class="flex flex-col gap-4">
      <AccountHistorySelectors
        v-model:account="modelAccount"
        v-model:asset="modelAsset"
        v-model:location="modelLocation"
        v-model:range="modelRange"
        :assets="assets"
        :assets-loading="assetsLoading"
        :assets-processing-required="assetsProcessingRequired"
        :restrict-assets="premium"
        :locations="locations"
      />

      <AccountHistorySummary
        v-if="premium"
        :asset="picked && !error ? selection.asset : undefined"
        :summary="summary"
        :processing-required="processingRequired"
      />

      <AccountBalanceChart
        :buckets="buckets"
        :total="total"
        :loading="loading"
      >
        <template
          v-if="placeholder"
          #placeholder
        >
          <GetPremiumPlaceholder
            v-if="placeholder === 'premium'"
            :title="t('account_history.chart.title')"
            :description="t('account_history.premium_description')"
            data-testid="account-history-premium"
          />
          <div
            v-else-if="placeholder === 'error'"
            class="text-rui-error"
            data-testid="account-history-error"
          >
            {{ t('account_history.error', { message: error }) }}
          </div>
          <div
            v-else-if="placeholder === 'pick'"
            class="text-rui-text-secondary"
            data-testid="account-history-pick"
          >
            {{ t('account_history.pick') }}
          </div>
          <div
            v-else
            class="text-rui-text-secondary"
            data-testid="account-history-empty"
          >
            {{ processingRequired ? t('account_history.empty_processing') : t('account_history.empty') }}
          </div>
        </template>
      </AccountBalanceChart>

      <AccountHistoryEvents
        v-if="showEvents && selection.account && selection.asset"
        :account="selection.account"
        :asset="selection.asset"
        :location="selection.location"
        :range="eventsRange"
      />
    </div>
  </TablePageLayout>
</template>
