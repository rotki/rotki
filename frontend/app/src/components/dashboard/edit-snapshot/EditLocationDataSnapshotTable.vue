<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { LocationDataSnapshot, LocationDataSnapshotPayload } from '@/types/snapshots';
import { type BigNumber, bigNumberify, One, Zero } from '@rotki/common';
import EditLocationDataSnapshotForm from '@/components/dashboard/edit-snapshot/EditLocationDataSnapshotForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import RowActions from '@/components/helper/RowActions.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useConfirmStore } from '@/store/confirm';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';

const modelValue = defineModel<LocationDataSnapshot[]>({ required: true });

const props = defineProps<{
  timestamp: number;
}>();

const emit = defineEmits<{
  'update:step': [step: number];
}>();

const { t } = useI18n({ useScope: 'global' });

type IndexedLocationDataSnapshot = LocationDataSnapshot & { index: number };

const { timestamp } = toRefs(props);

const openDialog = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const submitting = ref<boolean>(false);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const editedIndex = ref<number | null>(null);
const formModel = ref<LocationDataSnapshotPayload | null>(null);
const excludedLocations = ref<string[]>([]);
const tableRef = ref<any>();
const sort = ref<DataTableSortData<LocationDataSnapshot>>({
  column: 'usdValue',
  direction: 'desc' as const,
});
const form = ref<InstanceType<typeof EditLocationDataSnapshotForm>>();

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

const { useExchangeRate } = usePriceUtils();
const fiatExchangeRate = computed<BigNumber>(() => get(useExchangeRate(get(currencySymbol))) ?? One);

const data = computed<IndexedLocationDataSnapshot[]>(() =>
  get(modelValue).map((item: LocationDataSnapshot, index: number) => ({ ...item, index })).filter((item: IndexedLocationDataSnapshot) => item.location !== 'total'),
);

function updateStep(step: number): void {
  emit('update:step', step);
}

function editClick(item: IndexedLocationDataSnapshot): void {
  set(editedIndex, item.index);

  const convertedFiatValue
    = get(currencySymbol) === CURRENCY_USD
      ? item.usdValue.toFixed()
      : item.usdValue.multipliedBy(get(fiatExchangeRate)).toFixed();

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
    timestamp: get(timestamp),
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
  const timestampVal = get(timestamp);

  const convertedUsdValue
    = get(currencySymbol) === CURRENCY_USD
      ? bigNumberify(formData.usdValue)
      : bigNumberify(formData.usdValue).dividedBy(get(fiatExchangeRate));

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

const total = computed<BigNumber>(() => {
  const totalEntry = get(modelValue).find((item: LocationDataSnapshot) => item.location === 'total');

  if (!totalEntry)
    return Zero;

  return totalEntry.usdValue;
});

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
    <RuiDataTable
      ref="tableRef"
      v-model:sort="sort"
      class="table-inside-dialog !max-h-[calc(100vh-26.25rem)]"
      :cols="tableHeaders"
      :rows="data"
      :scroller="tableRef?.$el"
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
        <AmountDisplay
          :value="row.usdValue"
          fiat-currency="USD"
        />
      </template>

      <template #item.action="{ row }">
        <RowActions
          :edit-tooltip="t('dashboard.snapshot.edit.dialog.actions.edit_item')"
          :delete-tooltip="t('dashboard.snapshot.edit.dialog.actions.delete_item')"
          @edit-click="editClick(row)"
          @delete-click="showDeleteConfirmation(row)"
        />
      </template>
    </RuiDataTable>
    <div
      class="border-t-2 border-rui-grey-300 dark:border-rui-grey-800 relative z-[2] flex items-center justify-between gap-4 p-2"
    >
      <div>
        <div class="text-caption">
          {{ t('common.total') }}:
        </div>
        <div class="font-bold text-h6 -mt-1">
          <AmountDisplay
            :value="total"
            :amount="total"
            :price-asset="CURRENCY_USD"
            :fiat-currency="CURRENCY_USD"
            :timestamp="timestamp"
          />
        </div>
      </div>

      <div class="flex gap-2">
        <RuiButton
          variant="text"
          color="primary"
          @click="add()"
        >
          <template #prepend>
            <RuiIcon name="lu-circle-plus" />
          </template>
          {{ t('dashboard.snapshot.edit.dialog.actions.add_new_entry') }}
        </RuiButton>
        <RuiButton
          variant="text"
          @click="updateStep(1)"
        >
          <template #prepend>
            <RuiIcon name="lu-arrow-left" />
          </template>
          {{ t('common.actions.back') }}
        </RuiButton>
        <RuiButton
          color="primary"
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
