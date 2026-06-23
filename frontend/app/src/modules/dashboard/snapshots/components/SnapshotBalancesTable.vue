<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { BalanceSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import type { BalanceMutation, LocationAttribution } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { type BigNumber, toSentenceCase } from '@rotki/common';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { isNft } from '@/modules/assets/nft-utils';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import { BalanceType } from '@/modules/balances/types/balances';
import TableStatusFilter from '@/modules/core/table/TableStatusFilter.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import SnapshotBalanceDeleteDialog from '@/modules/dashboard/snapshots/components/SnapshotBalanceDeleteDialog.vue';
import SnapshotBalanceEntryDialog from '@/modules/dashboard/snapshots/components/SnapshotBalanceEntryDialog.vue';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import { useSnapshotAssetFilters } from '@/modules/dashboard/snapshots/composables/use-snapshot-asset-filters';
import { getTotalValue } from '@/modules/dashboard/snapshots/utils/snapshot-totals';
import { getSnapshotWarnings, type SnapshotWarning } from '@/modules/dashboard/snapshots/utils/snapshot-warnings';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import RowActions from '@/modules/shell/components/RowActions.vue';

type CategoryFilter = 'all' | 'asset' | 'liability' | 'nft';

type IndexedBalanceSnapshot = BalanceSnapshot & { index: number; categoryLabel: string };

const { locked = false, snapshot, timestamp } = defineProps<{
  snapshot: Snapshot;
  timestamp: number;
  /** Disables every edit action while the snapshot's totals don't reconcile. */
  locked?: boolean;
}>();

const emit = defineEmits<{
  'add': [mutation: BalanceMutation];
  'edit': [payload: { index: number; mutation: BalanceMutation }];
  'delete': [payload: { index: number; location: LocationAttribution }];
  'bulk-delete': [indices: number[]];
}>();

const { t } = useI18n({ useScope: 'global' });

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { getAssetField } = useAssetInfoRetrieval();
const { isIgnoredAsset, isSpamAsset } = useSnapshotAssetFilters();

const search = ref<string>('');
// Debounced so the per-keystroke filter doesn't rebuild the asset haystack for
// every row (each row reads symbol/name) on a large snapshot.
const debouncedSearch = refDebounced(search, 300);
const categoryFilter = ref<CategoryFilter>('all');
const filterMenu = ref<boolean>(false);
const hideSpam = ref<boolean>(true);
const hideIgnored = ref<boolean>(true);
const hideZeroValue = ref<boolean>(true);
const sort = ref<DataTableSortData<BalanceSnapshot>>({
  column: 'usdValue',
  direction: 'desc',
});
const entryDialog = useTemplateRef<InstanceType<typeof SnapshotBalanceEntryDialog>>('entryDialog');
const deleteDialog = useTemplateRef<InstanceType<typeof SnapshotBalanceDeleteDialog>>('deleteDialog');

const categoryOptions = computed<{ key: CategoryFilter; label: string }[]>(() => [
  { key: 'all', label: t('dashboard.snapshot.detail.balances.all') },
  { key: 'asset', label: t('dashboard.snapshot.detail.balances.asset') },
  { key: 'liability', label: t('dashboard.snapshot.detail.balances.liability') },
  { key: 'nft', label: t('dashboard.snapshot.detail.balances.nft') },
]);

/**
 * Row indices flagged by a sanity warning, mapped to their warnings. Zero-value
 * rows are excluded: they are overwhelmingly valueless spam tokens, so flagging
 * each one floods the table — the summary surfaces their count instead.
 */
const warningsByIndex = computed<Map<number, SnapshotWarning[]>>(() => {
  const map = new Map<number, SnapshotWarning[]>();
  for (const warning of getSnapshotWarnings(snapshot)) {
    if (warning.balanceIndex === undefined || warning.code === 'zero-value')
      continue;
    const list = map.get(warning.balanceIndex) ?? [];
    list.push(warning);
    map.set(warning.balanceIndex, list);
  }
  return map;
});

const data = computed<IndexedBalanceSnapshot[]>(() =>
  snapshot.balancesSnapshot.map((item: BalanceSnapshot, index: number) => ({
    ...item,
    categoryLabel: isNft(item.assetIdentifier)
      ? `${item.category} (${t('dashboard.snapshot.detail.balances.nft')})`
      : item.category,
    index,
  })),
);

/** Lower-cased symbol/name/identifier haystack so the text filter matches what the user reads. */
function haystack(identifier: string): string {
  const symbol = getAssetField(identifier, 'symbol');
  const name = getAssetField(identifier, 'name');
  return `${identifier} ${symbol} ${name}`.toLowerCase();
}

function matchesCategory(item: IndexedBalanceSnapshot): boolean {
  switch (get(categoryFilter)) {
    case 'asset':
      return item.category === BalanceType.ASSET && !isNft(item.assetIdentifier);
    case 'liability':
      return item.category === BalanceType.LIABILITY;
    case 'nft':
      return isNft(item.assetIdentifier);
    case 'all':
    default:
      return true;
  }
}

/** Counts of each hideable row kind, shown next to their filter checkboxes. */
const spamCount = computed<number>(() => get(data).filter(item => isSpamAsset(item.assetIdentifier)).length);
const ignoredCount = computed<number>(() => get(data).filter(item => isIgnoredAsset(item.assetIdentifier)).length);
const zeroValueCount = computed<number>(() => get(data).filter(item => item.usdValue.isZero()).length);

const filteredData = computed<IndexedBalanceSnapshot[]>(() => {
  const text = get(debouncedSearch).toLowerCase().trim();
  const hideSpamRows = get(hideSpam);
  const hideIgnoredRows = get(hideIgnored);
  const hideZeroValueRows = get(hideZeroValue);
  return get(data).filter(item =>
    matchesCategory(item)
    && (!hideSpamRows || !isSpamAsset(item.assetIdentifier))
    && (!hideIgnoredRows || !isIgnoredAsset(item.assetIdentifier))
    && (!hideZeroValueRows || !item.usdValue.isZero())
    && (!text || haystack(item.assetIdentifier).includes(text)),
  );
});

const total = computed<BigNumber>(() => getTotalValue(snapshot.locationDataSnapshot));

/** Rows hidden by the active hide-filters, surfaced next to the filter button. */
const hiddenCount = computed<number>(() => get(data).filter(item =>
  (get(hideSpam) && isSpamAsset(item.assetIdentifier))
  || (get(hideIgnored) && isIgnoredAsset(item.assetIdentifier))
  || (get(hideZeroValue) && item.usdValue.isZero()),
).length);

const emptyDescription = computed<string>(() =>
  get(data).length > 0 && get(filteredData).length === 0
    ? t('dashboard.snapshot.detail.balances.empty_filtered')
    : t('dashboard.snapshot.detail.balances.empty'),
);

const isLiability = (item: IndexedBalanceSnapshot): boolean => item.category === BalanceType.LIABILITY;

/**
 * Signed share of net worth: assets contribute positively, liabilities negatively
 * (net worth = assets − liabilities). Empty when net worth is not positive, where
 * the ratio would be meaningless.
 */
function sharePercent(item: IndexedBalanceSnapshot): string {
  const net = get(total);
  if (!net.isPositive())
    return '';
  const contribution = isLiability(item) ? item.usdValue.negated() : item.usdValue;
  return contribution.dividedBy(net).multipliedBy(100).toFormat(2);
}

/** Short, asset-agnostic reason for a row's sanity flag (shown in its tooltip). */
function describeWarning(warning: SnapshotWarning): string {
  switch (warning.code) {
    case 'negative-balance':
      return t('dashboard.snapshot.detail.balances.flag_reasons.negative');
    case 'duplicate-asset':
      return t('dashboard.snapshot.detail.balances.flag_reasons.duplicate');
    case 'nft-amount':
      return t('dashboard.snapshot.detail.balances.flag_reasons.nft_amount');
    default:
      return t('dashboard.snapshot.detail.balances.flagged');
  }
}

function categoryChipColor(item: IndexedBalanceSnapshot): 'error' | 'info' | 'grey' {
  if (isLiability(item))
    return 'error';
  if (isNft(item.assetIdentifier))
    return 'info';
  return 'grey';
}

const tableHeaders = computed<DataTableColumn<IndexedBalanceSnapshot>[]>(() => [
  {
    cellClass: 'py-2',
    class: 'w-[10rem]',
    key: 'categoryLabel',
    label: t('common.category'),
    sortable: true,
  },
  {
    cellClass: 'py-0 max-w-[20rem]',
    class: 'max-w-[20rem]',
    key: 'assetIdentifier',
    label: t('common.asset'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'amount',
    label: t('common.amount'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'usdValue',
    label: t('common.value_in_symbol', { symbol: get(currencySymbol) }),
    sortable: true,
  },
  {
    align: 'end',
    class: 'w-[6rem]',
    key: 'share',
    label: t('dashboard.snapshot.detail.balances.share'),
  },
  {
    cellClass: 'py-2',
    class: 'w-[6.25rem]',
    key: 'action',
    label: '',
  },
]);

useRememberTableSorting<BalanceSnapshot>(TableId.EDIT_BALANCE_SNAPSHOT, sort, tableHeaders);

function add(): void {
  get(entryDialog)?.openAdd();
}

function editClick(item: IndexedBalanceSnapshot): void {
  get(entryDialog)?.openEdit(item);
}

function onSubmit(payload: { index: number | null; mutation: BalanceMutation }): void {
  if (payload.index === null)
    emit('add', payload.mutation);
  else
    emit('edit', { index: payload.index, mutation: payload.mutation });
}

function deleteClick(item: IndexedBalanceSnapshot): void {
  get(deleteDialog)?.open(item.index);
}

/**
 * Sweep away the valueless rows in one step. Only zero-value balances are
 * eligible: removing them never debits a location subtotal (their value is 0),
 * so the sweep stays correct without asking for a per-row location like the
 * single delete does. The page owns the confirmation.
 */
function bulkDeleteZeroValue(): void {
  const indices = get(data).filter(item => item.usdValue.isZero()).map(item => item.index);
  if (indices.length > 0) {
    set(filterMenu, false);
    emit('bulk-delete', indices);
  }
}

function onDelete(payload: { index: number; location: LocationAttribution }): void {
  emit('delete', payload);
}
</script>

<template>
  <RuiCard
    no-padding
    data-testid="snapshot-balances-table"
  >
    <template #custom-header>
      <div class="flex flex-wrap items-center justify-between gap-4 p-4 border-b border-default">
        <h5 class="text-h6">
          {{ t('dashboard.snapshot.detail.balances.title') }}
        </h5>
        <div class="flex flex-wrap items-center gap-2">
          <TableStatusFilter v-model="filterMenu">
            <div
              class="p-2 flex flex-col gap-1 min-w-[12rem]"
              data-testid="snapshot-balances-filter-menu"
            >
              <div class="font-bold uppercase px-3 py-1 text-sm text-rui-text-secondary">
                {{ t('dashboard.snapshot.detail.balances.hide_title') }}
              </div>
              <RuiCheckbox
                v-model="hideSpam"
                color="primary"
                class="mt-0 px-3"
                hide-details
                :label="t('dashboard.snapshot.detail.balances.hide_spam', { count: spamCount }, spamCount)"
                data-testid="snapshot-balances-hide-spam"
              />
              <RuiCheckbox
                v-model="hideIgnored"
                color="primary"
                class="mt-0 px-3"
                hide-details
                :label="t('dashboard.snapshot.detail.balances.hide_ignored', { count: ignoredCount }, ignoredCount)"
                data-testid="snapshot-balances-hide-ignored"
              />
              <RuiCheckbox
                v-model="hideZeroValue"
                color="primary"
                class="mt-0 px-3"
                hide-details
                :label="t('dashboard.snapshot.detail.balances.hide_zero_value', { count: zeroValueCount }, zeroValueCount)"
                data-testid="snapshot-balances-hide-zero-value"
              />
              <div
                v-if="zeroValueCount > 0"
                class="border-t border-default my-1"
              />
              <RuiButton
                v-if="zeroValueCount > 0"
                variant="text"
                color="error"
                size="sm"
                class="justify-start gap-2"
                :disabled="locked"
                data-testid="snapshot-balances-bulk-delete"
                @click="bulkDeleteZeroValue()"
              >
                <RuiIcon
                  name="lu-trash-2"
                  size="18"
                />
                {{ t('dashboard.snapshot.detail.balances.bulk_delete.action', { count: zeroValueCount }, zeroValueCount) }}
              </RuiButton>
            </div>
          </TableStatusFilter>
          <RuiChip
            v-if="hiddenCount > 0"
            size="sm"
            class="whitespace-nowrap"
            data-testid="snapshot-balances-hidden-count"
          >
            {{ t('dashboard.snapshot.detail.balances.hidden', { count: hiddenCount }, hiddenCount) }}
          </RuiChip>
          <RuiMenuSelect
            v-model="categoryFilter"
            :options="categoryOptions"
            key-attr="key"
            text-attr="label"
            :label="t('dashboard.snapshot.detail.balances.category')"
            variant="outlined"
            hide-details
            dense
            class="w-44"
            data-testid="snapshot-balances-category"
          />
          <RuiTextField
            v-model="search"
            variant="outlined"
            color="primary"
            dense
            hide-details
            clearable
            class="w-60"
            :label="t('dashboard.snapshot.detail.balances.search')"
            data-testid="snapshot-balances-search"
          >
            <template #prepend>
              <RuiIcon
                name="lu-search"
                size="18"
              />
            </template>
          </RuiTextField>
          <RuiButton
            color="primary"
            size="sm"
            class="!py-2"
            :disabled="locked"
            data-testid="snapshot-balances-add"
            @click="add()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-circle-plus"
                size="18"
              />
            </template>
            {{ t('dashboard.snapshot.detail.balances.add') }}
          </RuiButton>
        </div>
      </div>
    </template>

    <RuiAlert
      v-if="locked"
      type="warning"
      class="mx-4 mt-4"
      data-testid="snapshot-balances-locked"
    >
      {{ t('dashboard.snapshot.detail.balances.locked') }}
    </RuiAlert>

    <RuiDataTable
      v-model:sort="sort"
      :cols="tableHeaders"
      :rows="filteredData"
      :empty="{ description: emptyDescription }"
      row-attr="assetIdentifier"
      dense
    >
      <template #item.categoryLabel="{ row }">
        <RuiChip
          size="sm"
          :color="categoryChipColor(row)"
        >
          {{ toSentenceCase(row.categoryLabel) }}
        </RuiChip>
      </template>

      <template #item.assetIdentifier="{ row }">
        <div class="flex items-center gap-2 min-w-0">
          <RuiTooltip
            v-if="warningsByIndex.has(row.index)"
            :open-delay="200"
          >
            <template #activator>
              <RuiIcon
                name="lu-triangle-alert"
                size="18"
                class="text-rui-warning shrink-0"
                data-testid="snapshot-balances-flag"
              />
            </template>
            <ul class="list-disc pl-4">
              <li
                v-for="warning in warningsByIndex.get(row.index)"
                :key="warning.code"
              >
                {{ describeWarning(warning) }}
              </li>
            </ul>
          </RuiTooltip>
          <AssetDetails
            v-if="!isNft(row.assetIdentifier)"
            class="min-w-0 [&_.avatar]:ml-1.5 [&_.avatar]:mr-2"
            :asset="row.assetIdentifier"
            :enable-association="false"
            hide-menu
          />
          <NftDetails
            v-else
            class="min-w-0"
            :identifier="row.assetIdentifier"
          />
        </div>
      </template>

      <template #item.amount="{ row }">
        <ValueDisplay :value="row.amount" />
      </template>

      <template #item.usdValue="{ row }">
        <SnapshotFiatDisplay
          :value="row.usdValue"
          :timestamp="timestamp"
          :class="{ 'text-rui-error': isLiability(row) }"
        />
      </template>

      <template #item.share="{ row }">
        <span
          v-if="sharePercent(row)"
          class="text-body-2"
          :class="isLiability(row) ? 'text-rui-error' : 'text-rui-text-secondary'"
        >
          {{ t('dashboard.snapshot.detail.balances.share_percent', { percent: sharePercent(row) }) }}
        </span>
      </template>

      <template #item.action="{ row }">
        <RowActions
          :disabled="locked"
          :edit-tooltip="t('dashboard.snapshot.edit.dialog.actions.edit_item')"
          :delete-tooltip="t('dashboard.snapshot.edit.dialog.actions.delete_item')"
          @edit-click="editClick(row)"
          @delete-click="deleteClick(row)"
        />
      </template>

      <template #tfoot>
        <tr>
          <td
            colspan="3"
            class="font-medium p-4"
          >
            {{ t('common.total') }}
          </td>
          <td class="text-right font-bold p-4">
            <SnapshotFiatDisplay
              :value="total"
              :timestamp="timestamp"
            />
          </td>
          <td />
          <td />
        </tr>
      </template>
    </RuiDataTable>

    <SnapshotBalanceEntryDialog
      ref="entryDialog"
      :snapshot="snapshot"
      :timestamp="timestamp"
      @submit="onSubmit($event)"
    />

    <SnapshotBalanceDeleteDialog
      ref="deleteDialog"
      :snapshot="snapshot"
      :timestamp="timestamp"
      @confirm="onDelete($event)"
    />
  </RuiCard>
</template>
