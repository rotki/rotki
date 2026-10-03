<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn } from '@rotki/ui-library';
import type { HistoricalBucket } from '@/modules/statistics/historical-balances/historical-balances-grouping';
import type { PriceStatus } from '@/modules/statistics/historical-balances/use-historical-balance-values';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { fitsEveryLimit } from '@/modules/session/use-items-per-page';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import HistoricalBalanceValueCell from '@/modules/statistics/historical-balances/components/HistoricalBalanceValueCell.vue';

interface BucketRow extends HistoricalBucket {
  id: string;
}

const { buckets, price, priceStatus } = defineProps<{
  buckets: HistoricalBucket[];
  /** The asset's price at the as-of time, in the user's currency; undefined unless priced. */
  price: BigNumber | undefined;
  priceStatus: PriceStatus;
}>();

const { t } = useI18n({ useScope: 'global' });

const rows = computed<BucketRow[]>(() => buckets.map(bucket => ({
  ...bucket,
  id: `${bucket.location}|${bucket.locationLabel ?? ''}|${bucket.protocol ?? ''}`,
})));

const cols = computed<DataTableColumn<BucketRow>[]>(() => [
  { cellClass: 'py-1', class: 'w-full', key: 'location', label: t('common.account') },
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
      <template #item.location="{ row }">
        <HistoryEventAccount
          v-if="row.locationLabel"
          :location="row.location"
          :location-label="row.locationLabel"
        />
        <LocationDisplay
          v-else
          :identifier="row.location"
          class="w-fit"
          horizontal
        />
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
          :value="price ? row.amount.times(price) : undefined"
          :status="priceStatus"
        />
      </template>
    </RuiDataTable>
  </div>
</template>
