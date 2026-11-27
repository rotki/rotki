<script setup lang="ts">
import { RuiAlert, RuiButton, RuiIcon } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import AccountHistoryEvents from '@/modules/balances/account-history/components/AccountHistoryEvents.vue';
import AccountHistorySelectors from '@/modules/balances/account-history/components/AccountHistorySelectors.vue';
import AccountHistorySummary from '@/modules/balances/account-history/components/AccountHistorySummary.vue';
import AccountBalanceChart from '@/modules/balances/account-history/components/chart/AccountBalanceChart.vue';
import { useAccountHistory } from '@/modules/balances/account-history/use-account-history';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const {
  assets,
  assetsLoading,
  assetsProcessingRequired,
  buckets,
  empty,
  error,
  loadedRange,
  loading,
  locations,
  modelAccount,
  modelAsset,
  modelLocation,
  modelRange,
  processingRequired,
  refresh,
  selection,
  summary,
  total,
} = useAccountHistory();
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.balances'), t('navigation_menu.balances_sub.account_history')]">
    <template #buttons>
      <RuiButton
        variant="outlined"
        color="primary"
        :loading="loading"
        :disabled="!selection.account || !selection.asset"
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
        :locations="locations"
      />

      <RuiAlert
        v-if="error"
        type="error"
        data-testid="account-history-error"
      >
        {{ t('account_history.error', { message: error }) }}
      </RuiAlert>

      <RuiAlert
        v-else-if="!selection.account || !selection.asset"
        type="info"
        data-testid="account-history-pick"
      >
        {{ t('account_history.pick') }}
      </RuiAlert>

      <template v-else>
        <AccountHistorySummary
          :asset="selection.asset"
          :summary="summary"
          :processing-required="processingRequired"
        />

        <RuiAlert
          v-if="empty"
          type="info"
          data-testid="account-history-empty"
        >
          {{ processingRequired ? t('account_history.empty_processing') : t('account_history.empty') }}
        </RuiAlert>

        <AccountBalanceChart
          v-else
          :buckets="buckets"
          :total="total"
        />

        <AccountHistoryEvents
          :account="selection.account"
          :asset="selection.asset"
          :location="selection.location"
          :range="loadedRange"
        />
      </template>
    </div>
  </TablePageLayout>
</template>
