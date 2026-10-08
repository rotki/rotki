<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { HistoricalBucketRow } from '@/modules/statistics/historical-balances/historical-balances-view';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
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
  { align: 'end', cellClass: 'py-1', key: 'value', label: t('common.value') },
]);

const hidePagination = computed<boolean>(() => fitsEveryLimit(buckets.length));
</script>

<template>
  <div class="my-2 bg-white dark:bg-dark-elevated rounded-xl">
    <RuiDataTable
      :cols="cols"
      :rows="rows"
      row-attr="id"
      :hide-default-header="hidePagination"
      :hide-default-footer="hidePagination"
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
    </RuiDataTable>
  </div>
</template>
