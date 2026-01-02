<script setup lang="ts">
import AssetBalances from '@/components/AssetBalances.vue';
import GetPremiumPlaceholder from '@/components/common/GetPremiumPlaceholder.vue';
import HistoryEventsAlert from '@/components/history/HistoryEventsAlert.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useHistoricalBalances } from '@/composables/balances/historical';
import { usePremium } from '@/composables/premium';

const { t } = useI18n({ useScope: 'global' });
const premium = usePremium();

const {
  dialogOpen,
  timestamp,
  selectedAsset,
  balances,
  loading,
  errorMessage,
  hasResults,
  fetchBalances,
  closeDialog,
} = useHistoricalBalances();
</script>

<template>
  <RuiDialog
    v-model="dialogOpen"
    max-width="800"
    @closed="closeDialog()"
  >
    <RuiCard>
      <template #header>
        {{ t('historical_balances_dialog.title') }}
      </template>
      <template #subheader>
        {{ t('historical_balances_dialog.hint') }}
      </template>

      <GetPremiumPlaceholder
        v-if="!premium"
        :title="t('historical_balances_dialog.title')"
        :description="t('historical_balances_dialog.premium_required')"
      />

      <template v-else>
        <div class="flex flex-col gap-4">
          <HistoryEventsAlert />

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <DateTimePicker
              v-model="timestamp"
              variant="outlined"
              :label="t('historical_balances_dialog.timestamp_label')"
              max-date="now"
              type="epoch"
              accuracy="second"
            />

            <AssetSelect
              v-model="selectedAsset"
              clearable
              variant="outlined"
              :hint="t('historical_balances_dialog.asset_hint')"
            />
          </div>

          <RuiButton
            color="primary"
            :loading="loading"
            size="lg"
            @click="fetchBalances()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-search"
                size="20"
              />
            </template>
            {{ t('historical_balances_dialog.fetch_button') }}
          </RuiButton>

          <div
            v-if="loading"
            class="text-rui-text-secondary text-body-2 -mt-2"
          >
            {{ t('historical_balances_dialog.task_running_hint') }}
          </div>

          <RuiAlert
            v-if="errorMessage"
            type="error"
          >
            {{ errorMessage }}
          </RuiAlert>

          <template v-if="hasResults">
            <RuiDivider class="my-2" />

            <AssetBalances
              :balances="balances"
              :loading="loading"
              hide-total
              class="table-inside-dialog !max-h-[calc(100vh-30rem)]"
              hide-breakdown
            />
          </template>
        </div>
      </template>

      <template #footer>
        <div class="w-full" />
        <RuiButton
          color="primary"
          variant="text"
          @click="dialogOpen = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
