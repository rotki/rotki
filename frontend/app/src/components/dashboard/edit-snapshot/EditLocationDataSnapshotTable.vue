<script setup lang="ts">
import { CURRENCY_USD } from '@/types/currencies';
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { LocationDataSnapshot, LocationDataSnapshotPayload } from '@/types/snapshots';

const props = defineProps<{
  modelValue: LocationDataSnapshot[];
  timestamp: number;
}>();

const emit = defineEmits<{
  (e: 'update:step', step: number): void;
  (e: 'update:model-value', value: LocationDataSnapshot[]): void;
}>();

const { t } = useI18n();

type IndexedLocationDataSnapshot = LocationDataSnapshot & { index: number };

const { openDialog, setOpenDialog, closeDialog, submitting, setSubmitFunc, trySubmit } = useEditLocationsSnapshotForm();

const { timestamp } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const editedIndex = ref<number | null>(null);
const form = ref<LocationDataSnapshotPayload | null>(null);
const excludedLocations = ref<string[]>([]);
const tableRef = ref<any>();
const sort = ref<DataTableSortData<LocationDataSnapshot>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const tableHeaders = computed<DataTableColumn<IndexedLocationDataSnapshot>[]>(() => [
  {
    label: t('common.location'),
    key: 'location',
    class: 'w-[12.5rem]',
    cellClass: 'py-2',
    align: 'center',
    sortable: true,
  },
  {
    label: t('common.value_in_symbol', { symbol: get(currencySymbol) }),
    key: 'usdValue',
    align: 'end',
    sortable: true,
  },
  {
    label: '',
    key: 'action',
    class: 'w-[6.25rem]',
    cellClass: 'py-2',
  },
]);

const { exchangeRate } = useBalancePricesStore();
const fiatExchangeRate = computed<BigNumber>(() => get(exchangeRate(get(currencySymbol))) ?? One);

const data = computed<IndexedLocationDataSnapshot[]>(() =>
  props.modelValue.map((item, index) => ({ ...item, index })).filter(item => item.location !== 'total'),
);

function input(value: LocationDataSnapshot[]) {
  emit('update:model-value', value);
}

function updateStep(step: number) {
  emit('update:step', step);
}

function editClick(item: IndexedLocationDataSnapshot) {
  set(editedIndex, item.index);

  const convertedFiatValue
    = get(currencySymbol) === CURRENCY_USD
      ? item.usdValue.toFixed()
      : item.usdValue.multipliedBy(get(fiatExchangeRate)).toFixed();

  set(form, {
    ...item,
    usdValue: convertedFiatValue,
  });

  set(
    excludedLocations,
    props.modelValue.map(item => item.location).filter(identifier => identifier !== item.location),
  );

  setOpenDialog(true);
}

function add() {
  set(editedIndex, null);
  set(form, {
    timestamp: get(timestamp),
    location: '',
    usdValue: '',
  });
  set(
    excludedLocations,
    props.modelValue.map(item => item.location),
  );
  setOpenDialog(true);
}

function save() {
  const formVal = get(form);

  if (!formVal)
    return;

  const index = get(editedIndex);
  const val = props.modelValue;
  const timestampVal = get(timestamp);

  const convertedUsdValue
    = get(currencySymbol) === CURRENCY_USD
      ? bigNumberify(formVal.usdValue)
      : bigNumberify(formVal.usdValue).dividedBy(get(fiatExchangeRate));

  const newValue = [...val];
  const payload = {
    timestamp: timestampVal,
    location: formVal.location,
    usdValue: convertedUsdValue,
  };

  if (index !== null)
    newValue[index] = payload;
  else newValue.unshift(payload);

  input(newValue);
  clearEditDialog();
}

setSubmitFunc(save);

function clearEditDialog() {
  closeDialog();
  set(editedIndex, null);
  set(form, null);
  set(excludedLocations, []);
}

function updateForm(newForm: LocationDataSnapshotPayload) {
  set(form, newForm);
}

function confirmDelete(index: number) {
  const val = props.modelValue;

  if (index === null)
    return;

  const newValue = [...val];
  newValue.splice(index, 1);

  input(newValue);
}

const total = computed<BigNumber>(() => {
  const totalEntry = props.modelValue.find(item => item.location === 'total');

  if (!totalEntry)
    return Zero;

  return totalEntry.usdValue;
});

const { show } = useConfirmStore();

function showDeleteConfirmation(item: IndexedLocationDataSnapshot) {
  show(
    {
      title: t('dashboard.snapshot.edit.dialog.location_data.delete_title'),
      message: t('dashboard.snapshot.edit.dialog.location_data.delete_confirmation'),
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
            <RuiIcon name="add-circle-line" />
          </template>
          {{ t('dashboard.snapshot.edit.dialog.actions.add_new_entry') }}
        </RuiButton>
        <RuiButton
          variant="text"
          @click="updateStep(1)"
        >
          <template #prepend>
            <RuiIcon name="arrow-left-line" />
          </template>
          {{ t('common.actions.back') }}
        </RuiButton>
        <RuiButton
          color="primary"
          @click="updateStep(3)"
        >
          {{ t('common.actions.next') }}
          <template #append>
            <RuiIcon name="arrow-right-line" />
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
      @confirm="trySubmit()"
      @cancel="clearEditDialog()"
    >
      <EditLocationDataSnapshotForm
        v-if="form"
        :form="form"
        :excluded-locations="excludedLocations"
        @update:form="updateForm($event)"
      />
    </BigDialog>
  </div>
</template>
