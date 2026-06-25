<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { LocationDataSnapshot, LocationDataSnapshotPayload } from '@/modules/dashboard/snapshots';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import EditLocationDataSnapshotForm from '@/modules/dashboard/edit-snapshot/EditLocationDataSnapshotForm.vue';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import { useHistoricFiatConversion } from '@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion';
import { convertFiatToUsd, convertUsdToFiat } from '@/modules/dashboard/snapshots/lib/snapshot-fx';
import { getTotalValue, TOTAL_LOCATION } from '@/modules/dashboard/snapshots/lib/snapshot-totals';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const modelValue = defineModel<LocationDataSnapshot[]>({ required: true });

const { timestamp } = defineProps<{
  timestamp: number;
}>();

const emit = defineEmits<{
  'update:step': [step: number];
}>();

const { t } = useI18n({ useScope: 'global' });

type IndexedLocationDataSnapshot = LocationDataSnapshot & { index: number };

const openDialog = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const submitting = ref<boolean>(false);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const editedIndex = ref<number | null>(null);
const formModel = ref<LocationDataSnapshotPayload | null>(null);
const excludedLocations = ref<string[]>([]);
const sort = ref<DataTableSortData<LocationDataSnapshot>>({
  column: 'usdValue',
  direction: 'desc' as const,
});
const form = useTemplateRef<InstanceType<typeof EditLocationDataSnapshotForm>>('form');

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
    cellClass: 'py-2',
    class: 'w-[6.25rem]',
    key: 'action',
    label: '',
  },
]);

useRememberTableSorting<LocationDataSnapshot>(TableId.EDIT_LOCATION_DATA_SNAPSHOT, sort, tableHeaders);

// Snapshots are stored in USD; editing in the user's fiat must use the
// historic USD -> fiat rate at the snapshot's timestamp, not today's (#12277).
const { isUsd, loading: fetchingRate, rate, rateReady } = useHistoricFiatConversion(() => timestamp);

const data = computed<IndexedLocationDataSnapshot[]>(() =>
  get(modelValue).map((item: LocationDataSnapshot, index: number) => ({ ...item, index })).filter((item: IndexedLocationDataSnapshot) => item.location !== TOTAL_LOCATION),
);

function updateStep(step: number): void {
  emit('update:step', step);
}

function editClick(item: IndexedLocationDataSnapshot): void {
  set(editedIndex, item.index);

  const convertedFiatValue
    = get(isUsd)
      ? item.usdValue.toFixed()
      : convertUsdToFiat(item.usdValue, get(rate)).toFixed();

  set(formModel, {
    ...item,
    usdValue: convertedFiatValue,
  });

  set(
    excludedLocations,
    get(modelValue).map((item: LocationDataSnapshot) => item.location).filter((identifier: string) => identifier !== item.location),
  );

  set(openDialog, true);
}

function add(): void {
  set(editedIndex, null);
  set(formModel, {
    location: '',
    timestamp,
    usdValue: '',
  });
  set(
    excludedLocations,
    get(modelValue).map((item: LocationDataSnapshot) => item.location),
  );
  set(openDialog, true);
}

async function save(): Promise<boolean> {
  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const formData = get(formModel);

  if (!formData)
    return false;

  set(submitting, true);
  const index = get(editedIndex);
  const val = get(modelValue);
  const timestampVal = timestamp;

  const convertedUsdValue
    = get(isUsd)
      ? bigNumberify(formData.usdValue)
      : convertFiatToUsd(bigNumberify(formData.usdValue), get(rate));

  const newValue = [...val];
  const payload = {
    location: formData.location,
    timestamp: timestampVal,
    usdValue: convertedUsdValue,
  };

  if (index !== null)
    newValue[index] = payload;
  else newValue.unshift(payload);

  set(submitting, false);

  set(modelValue, newValue);
  clearEditDialog();
  return true;
}

function clearEditDialog(): void {
  set(openDialog, false);
  set(editedIndex, null);
  set(formModel, null);
  set(excludedLocations, []);
}

function confirmDelete(index: number): void {
  const val = get(modelValue);

  if (index === null)
    return;

  const newValue = [...val];
  newValue.splice(index, 1);

  set(modelValue, newValue);
}

const total = computed<BigNumber>(() => getTotalValue(get(modelValue)));

const { show } = useConfirmStore();

function showDeleteConfirmation(item: IndexedLocationDataSnapshot) {
  show(
    {
      message: t('dashboard.snapshot.edit.dialog.location_data.delete_confirmation'),
      title: t('dashboard.snapshot.edit.dialog.location_data.delete_title'),
    },
    () => confirmDelete(item.index),
  );
}
</script>

<template>
  <div>
    <ScrollableDialogContent max-height="calc(100vh - 26.25rem)">
      <RuiDataTable
        v-model:sort="sort"
        :cols="tableHeaders"
        :rows="data"
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

        <template #item.action="{ row }">
          <RowActions
            :edit-disabled="!rateReady"
            :edit-tooltip="t('dashboard.snapshot.edit.dialog.actions.edit_item')"
            :delete-tooltip="t('dashboard.snapshot.edit.dialog.actions.delete_item')"
            @edit-click="editClick(row)"
            @delete-click="showDeleteConfirmation(row)"
          />
        </template>
      </RuiDataTable>
    </ScrollableDialogContent>
    <div
      class="border-t-2 border-rui-grey-300 dark:border-rui-grey-800 relative z-[2] flex items-center justify-between gap-4 p-2"
    >
      <div>
        <div class="text-caption">
          {{ t('common.total') }}:
        </div>
        <div class="font-bold text-h6 -mt-1">
          <SnapshotFiatDisplay
            :value="total"
            :timestamp="timestamp"
          />
        </div>
      </div>

      <div class="flex gap-2">
        <RuiButton
          variant="text"
          color="primary"
          :disabled="!rateReady"
          :loading="fetchingRate"
          @click="add()"
        >
          <template #prepend>
            <RuiIcon name="lu-circle-plus" />
          </template>
          {{ t('dashboard.snapshot.edit.dialog.actions.add_new_entry') }}
        </RuiButton>
        <RuiButton
          variant="text"
          data-testid="edit-snapshot-prev"
          @click="updateStep(1)"
        >
          <template #prepend>
            <RuiIcon name="lu-arrow-left" />
          </template>
          {{ t('common.actions.back') }}
        </RuiButton>
        <RuiButton
          color="primary"
          data-testid="edit-snapshot-next"
          @click="updateStep(3)"
        >
          {{ t('common.actions.next') }}
          <template #append>
            <RuiIcon name="lu-arrow-right" />
          </template>
        </RuiButton>
      </div>
    </div>

    <BigDialog
      :display="openDialog"
      :title="
        editedIndex !== null
          ? t('dashboard.snapshot.edit.dialog.location_data.edit_title')
          : t('dashboard.snapshot.edit.dialog.location_data.add_title')
      "
      :primary-action="t('common.actions.save')"
      :loading="submitting"
      :prompt-on-close="stateUpdated"
      @confirm="save()"
      @cancel="clearEditDialog()"
    >
      <EditLocationDataSnapshotForm
        v-if="formModel"
        ref="form"
        v-model="formModel"
        v-model:state-updated="stateUpdated"
        :excluded-locations="excludedLocations"
      />
    </BigDialog>
  </div>
</template>
