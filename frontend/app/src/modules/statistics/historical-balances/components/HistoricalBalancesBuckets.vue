<script setup lang="ts">
import type { HistoricalBucketRow } from '@/modules/statistics/historical-balances/historical-balances-view';
import { type DataTableColumn, RuiButton, RuiDataTable, RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { accountHistoryLink } from '@/modules/balances/account-history/account-history-selection';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { fitsEveryLimit } from '@/modules/session/use-items-per-page';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import HistoricalBalanceValueCell from '@/modules/statistics/historical-balances/components/HistoricalBalanceValueCell.vue';

interface BucketRow extends HistoricalBucketRow {
  id: string;
}

const { buckets, showAsset = false } = defineProps<{
  buckets: HistoricalBucketRow[];
  /** Name each bucket's asset, for a collection whose buckets hold different members. */
  showAsset?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const rows = computed<BucketRow[]>(() => buckets.map(bucket => ({
  ...bucket,
  id: `${bucket.asset}|${bucket.location}|${bucket.locationLabel ?? ''}|${bucket.protocol ?? ''}`,
})));

const cols = computed<DataTableColumn<BucketRow>[]>(() => [
  ...(showAsset ? [{ cellClass: 'py-1', key: 'asset', label: t('common.asset') }] : []),
  { cellClass: 'py-1', class: 'text-no-wrap', key: 'location', label: t('common.location') },
  { cellClass: 'py-1', class: 'w-full', key: 'locationLabel', label: t('common.account') },
  { cellClass: 'py-1', key: 'protocol', label: t('common.protocol') },
  { align: 'end', cellClass: 'py-1', key: 'amount', label: t('common.amount') },
  { align: 'end', cellClass: 'py-1 font-medium', key: 'value', label: t('common.value') },
  { align: 'end', cellClass: 'py-1', key: 'actions', label: '' },
]);

const hidePagination = computed<boolean>(() => fitsEveryLimit(buckets.length));
</script>

<template>
  <div class="my-2 bg-rui-surface rounded-xl">
    <RuiDataTable
      :cols="cols"
      :rows="rows"
      row-attr="id"
      :hide-pagination="hidePagination"
      dense
      outlined
      data-testid="historical-balances-buckets"
    >
      <template #item.asset="{ row }">
        <AssetDetails :asset="row.asset" />
      </template>
      <template #item.location="{ row }">
        <LocationDisplay
          :identifier="row.location"
          size="20px"
          class="w-fit"
          horizontal
          data-testid="historical-balances-bucket-location"
        />
      </template>
      <template #item.locationLabel="{ row }">
        <HistoryEventAccount
          v-if="row.locationLabel"
          :location="row.location"
          :location-label="row.locationLabel"
        />
        <span
          v-else
          class="text-rui-text-secondary"
        >
          -
        </span>
      </template>
      <template #item.protocol="{ row }">
        <CounterpartyDisplay
          v-if="row.protocol"
          :counterparty="row.protocol"
        />
        <span
          v-else
          class="text-rui-text-secondary"
        >
          -
        </span>
      </template>
      <template #item.amount="{ row }">
        <ValueDisplay :value="row.amount" />
      </template>
      <template #item.value="{ row }">
        <HistoricalBalanceValueCell
          :value="row.value"
          :status="row.priceStatus"
        />
      </template>
      <template #item.actions="{ row }">
        <RuiTooltip
          v-if="row.locationLabel"
          :open-delay="400"
        >
          <template #activator>
            <RouterLink
              :to="accountHistoryLink(row.locationLabel, row.asset, row.location)"
              :aria-label="t('account_history.view_history')"
              data-testid="historical-balances-bucket-history"
            >
              <RuiButton
                variant="text"
                icon
                size="sm"
              >
                <RuiIcon
                  name="lu-chart-line"
                  size="16"
                />
              </RuiButton>
            </RouterLink>
          </template>
          {{ t('account_history.view_history') }}
        </RuiTooltip>
      </template>
    </RuiDataTable>
  </div>
</template>
