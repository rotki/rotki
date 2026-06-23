<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { LocationDataSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import SnapshotLocationEntryDialog from '@/modules/dashboard/snapshots/components/SnapshotLocationEntryDialog.vue';
import SnapshotLocationSplit from '@/modules/dashboard/snapshots/components/SnapshotLocationSplit.vue';
import { findSumMismatch, type LocationSplit } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { getTotalValue, locationsTotal, TOTAL_LOCATION } from '@/modules/dashboard/snapshots/utils/snapshot-totals';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import RowActions from '@/modules/shell/components/RowActions.vue';

type IndexedLocationDataSnapshot = LocationDataSnapshot & { index: number };

/** Whether the drawer is shown. */
const open = defineModel<boolean>({ required: true });

const { snapshot, timestamp } = defineProps<{
  snapshot: Snapshot;
  timestamp: number;
}>();

const emit = defineEmits<{
  add: [location: LocationDataSnapshot];
  edit: [payload: { index: number; location: LocationDataSnapshot }];
  delete: [index: number];
  distribute: [splits: LocationSplit[]];
}>();

const { t } = useI18n({ useScope: 'global' });

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { show } = useConfirmStore();

const sort = ref<DataTableSortData<LocationDataSnapshot>>({
  column: 'usdValue',
  direction: 'desc',
});
const entryOpen = ref<boolean>(false);
const splitOpen = ref<boolean>(false);
const splits = ref<LocationSplit[]>([]);
const splitValid = ref<boolean>(false);
const entryDialog = useTemplateRef<InstanceType<typeof SnapshotLocationEntryDialog>>('entryDialog');

const data = computed<IndexedLocationDataSnapshot[]>(() =>
  snapshot.locationDataSnapshot
    .map((item: LocationDataSnapshot, index: number) => ({ ...item, index }))
    .filter(item => item.location !== TOTAL_LOCATION),
);

const storedTotal = computed<BigNumber>(() => getTotalValue(snapshot.locationDataSnapshot));
const allocated = computed<BigNumber>(() => locationsTotal(snapshot.locationDataSnapshot));
const mismatch = computed(() => findSumMismatch(snapshot));
const difference = computed<BigNumber>(() => get(storedTotal).minus(get(allocated)));
const locationNames = computed<string[]>(() => get(data).map(item => item.location));

/** A location's share of net worth; empty when net worth is not positive. */
function sharePercent(value: BigNumber): string {
  const net = get(storedTotal);
  return net.isPositive() ? value.dividedBy(net).multipliedBy(100).toFormat(2) : '';
}

const allocatedShare = computed<string>(() => sharePercent(get(allocated)));

const tableHeaders = computed<DataTableColumn<IndexedLocationDataSnapshot>[]>(() => [
  {
    align: 'center',
    cellClass: 'py-2',
    class: 'w-[12.5rem]',
    key: 'location',
    label: t('common.location'),
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
    label: t('dashboard.snapshot.detail.locations.share'),
  },
  {
    cellClass: 'py-2',
    class: 'w-[6.25rem]',
    key: 'action',
    label: '',
  },
]);

useRememberTableSorting<LocationDataSnapshot>(TableId.EDIT_LOCATION_DATA_SNAPSHOT, sort, tableHeaders);

function add(): void {
  get(entryDialog)?.openAdd();
}

function editClick(item: IndexedLocationDataSnapshot): void {
  get(entryDialog)?.openEdit(item);
}

function onSubmit(payload: { index: number | null; location: LocationDataSnapshot }): void {
  if (payload.index === null)
    emit('add', payload.location);
  else
    emit('edit', { index: payload.index, location: payload.location });
}

function showDeleteConfirmation(item: IndexedLocationDataSnapshot): void {
  show(
    {
      message: t('dashboard.snapshot.edit.dialog.location_data.delete_confirmation'),
      title: t('dashboard.snapshot.edit.dialog.location_data.delete_title'),
    },
    () => emit('delete', item.index),
  );
}

function applyDistribute(): void {
  if (!get(splitValid))
    return;
  emit('distribute', get(splits));
  set(splitOpen, false);
}
</script>

<template>
  <RuiNavigationDrawer
    v-model="open"
    width="560px"
    temporary
    position="right"
    :stateless="entryOpen"
    class="flex flex-col"
    content-class="flex flex-col"
    data-testid="snapshot-locations-drawer"
  >
    <div class="flex items-center justify-between gap-2 p-4 border-b border-default">
      <h5 class="text-h6">
        {{ t('dashboard.snapshot.detail.locations.title') }}
      </h5>
      <div class="flex items-center gap-2">
        <RuiButton
          color="primary"
          size="sm"
          data-testid="snapshot-locations-add"
          @click="add()"
        >
          <template #prepend>
            <RuiIcon name="lu-circle-plus" />
          </template>
          {{ t('dashboard.snapshot.detail.locations.add') }}
        </RuiButton>
        <RuiButton
          variant="text"
          icon
          size="sm"
          data-testid="snapshot-locations-close"
          @click="open = false"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </div>
    </div>

    <div class="overflow-y-auto grow p-4 flex flex-col gap-4">
      <RuiDataTable
        v-model:sort="sort"
        :cols="tableHeaders"
        :rows="data"
        :empty="{ description: t('dashboard.snapshot.detail.locations.empty') }"
        row-attr="location"
        dense
      >
        <template #item.location="{ row }">
          <LocationDisplay
            :opens-details="false"
            :identifier="row.location"
          />
        </template>

        <template #item.usdValue="{ row }">
          <SnapshotFiatDisplay
            :value="row.usdValue"
            :timestamp="timestamp"
          />
        </template>

        <template #item.share="{ row }">
          <span
            v-if="sharePercent(row.usdValue)"
            class="text-body-2 text-rui-text-secondary"
          >
            {{ t('dashboard.snapshot.detail.locations.share_percent', { percent: sharePercent(row.usdValue) }) }}
          </span>
        </template>

        <template #item.action="{ row }">
          <RowActions
            :edit-tooltip="t('dashboard.snapshot.edit.dialog.actions.edit_item')"
            :delete-tooltip="t('dashboard.snapshot.edit.dialog.actions.delete_item')"
            @edit-click="editClick(row)"
            @delete-click="showDeleteConfirmation(row)"
          />
        </template>

        <template #tfoot>
          <tr>
            <td class="font-medium p-4">
              {{ t('dashboard.snapshot.detail.locations.allocated') }}
            </td>
            <td class="text-right font-bold p-4">
              <SnapshotFiatDisplay
                :value="allocated"
                :timestamp="timestamp"
              />
            </td>
            <td class="text-right text-body-2 text-rui-text-secondary p-4">
              <span v-if="allocatedShare">
                {{ t('dashboard.snapshot.detail.locations.share_percent', { percent: allocatedShare }) }}
              </span>
            </td>
            <td />
          </tr>
          <tr>
            <td class="text-rui-text-secondary p-4 pt-0">
              {{ t('dashboard.snapshot.detail.locations.net_worth') }}
            </td>
            <td class="text-right text-rui-text-secondary p-4 pt-0">
              <SnapshotFiatDisplay
                :value="storedTotal"
                :timestamp="timestamp"
              />
            </td>
            <td colspan="2" />
          </tr>
        </template>
      </RuiDataTable>

      <div
        v-if="!mismatch"
        class="flex items-center gap-2 text-rui-success text-body-2"
        data-testid="snapshot-locations-balanced"
      >
        <RuiIcon
          name="lu-circle-check"
          size="18"
        />
        {{ t('dashboard.snapshot.detail.locations.balanced') }}
      </div>

      <RuiAlert
        v-if="mismatch"
        type="warning"
        data-testid="snapshot-locations-reconcile"
      >
        <template #title>
          {{ t('dashboard.snapshot.detail.locations.reconcile.title') }}
        </template>
        <p class="text-body-2 mb-3">
          <i18n-t
            scope="global"
            keypath="dashboard.snapshot.detail.locations.reconcile.description"
          >
            <template #amount>
              <SnapshotFiatDisplay
                class="font-medium"
                :value="difference"
                :timestamp="timestamp"
              />
            </template>
          </i18n-t>
        </p>
        <RuiButton
          v-if="!splitOpen"
          size="sm"
          color="warning"
          variant="outlined"
          data-testid="snapshot-locations-distribute"
          @click="splitOpen = true"
        >
          {{ t('dashboard.snapshot.detail.locations.reconcile.distribute') }}
        </RuiButton>

        <template v-if="splitOpen">
          <SnapshotLocationSplit
            v-model="splits"
            v-model:valid="splitValid"
            :total="storedTotal"
            :timestamp="timestamp"
            :locations="locationNames"
          />
          <div class="flex justify-end gap-2 mt-3">
            <RuiButton
              size="sm"
              variant="text"
              @click="splitOpen = false"
            >
              {{ t('common.actions.cancel') }}
            </RuiButton>
            <RuiButton
              size="sm"
              color="warning"
              :disabled="!splitValid"
              data-testid="snapshot-locations-distribute-apply"
              @click="applyDistribute()"
            >
              {{ t('common.actions.apply') }}
            </RuiButton>
          </div>
        </template>
      </RuiAlert>
    </div>

    <SnapshotLocationEntryDialog
      ref="entryDialog"
      v-model:open="entryOpen"
      :locations="snapshot.locationDataSnapshot"
      :timestamp="timestamp"
      @submit="onSubmit($event)"
    />
  </RuiNavigationDrawer>
</template>
