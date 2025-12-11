<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { BalanceSnapshot, BalanceSnapshotPayload, Snapshot } from '@/types/snapshots';
import { assert, type BigNumber, bigNumberify, One, toSentenceCase, Zero } from '@rotki/common';
import EditBalancesSnapshotForm from '@/components/dashboard/edit-snapshot/EditBalancesSnapshotForm.vue';
import EditBalancesSnapshotLocationSelector
  from '@/components/dashboard/edit-snapshot/EditBalancesSnapshotLocationSelector.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RowActions from '@/components/helper/RowActions.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import ConfirmSnapshotConflictReplacementDialog
  from '@/components/snapshots/ConfirmSnapshotConflictReplacementDialog.vue';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { BalanceType } from '@/types/balances';
import { CURRENCY_USD } from '@/types/currencies';
import { bigNumberSum } from '@/utils/calculation';
import { isNft } from '@/utils/nft';

const modelValue = defineModel<Snapshot>({ required: true });

const props = defineProps<{
  timestamp: number;
}>();

const emit = defineEmits<{
  'update:step': [step: number];
}>();

const { t } = useI18n({ useScope: 'global' });

type IndexedBalanceSnapshot = BalanceSnapshot & { index: number; categoryLabel: string };

const { timestamp } = toRefs(props);

const openDialog = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const submitting = ref<boolean>(false);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const showDeleteConfirmation = ref<boolean>(false);
const indexToEdit = ref<number | null>(null);
const indexToDelete = ref<number | null>(null);
const locationToDelete = ref<string>('');
const formModel = ref<(BalanceSnapshotPayload & { location: string }) | null>(null);
const tableRef = ref<any>();
const sort = ref<DataTableSortData<BalanceSnapshot>>({
  column: 'usdValue',
  direction: 'desc',
});
const assetSearch = ref<string>('');
const form = ref<InstanceType<typeof EditBalancesSnapshotForm>>();

const { useExchangeRate } = usePriceUtils();
const fiatExchangeRate = computed<BigNumber>(() => get(useExchangeRate(get(currencySymbol))) ?? One);

const data = computed<IndexedBalanceSnapshot[]>(() =>
  get(modelValue).balancesSnapshot.map((item: BalanceSnapshot, index: number) => ({
    ...item,
    categoryLabel: isNft(item.assetIdentifier)
      ? `${item.category} (${t('dashboard.snapshot.edit.dialog.balances.nft')})`
      : item.category,
    index,
  })),
);

const filteredData = computed<IndexedBalanceSnapshot[]>(() => {
  const allData = get(data);
  const search = get(assetSearch);
  if (!search)
    return allData;

  return allData.filter(({ assetIdentifier }) => assetIdentifier === search);
});

const total = computed<BigNumber>(() => {
  const totalEntry = get(modelValue).locationDataSnapshot.find(item => item.location === 'total');

  if (!totalEntry)
    return Zero;

  return totalEntry.usdValue;
});

const tableHeaders = computed<DataTableColumn<IndexedBalanceSnapshot>[]>(() => [
  {
    cellClass: 'py-2',
    class: 'w-[10rem]',
    key: 'categoryLabel',
    label: t('common.category'),
    sortable: true,
  },
  {
    cellClass: 'py-0',
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
    cellClass: 'py-2',
    class: 'w-[6.25rem]',
    key: 'action',
    label: '',
  },
]);

useRememberTableSorting<BalanceSnapshot>(TableId.EDIT_BALANCE_SNAPSHOT, sort, tableHeaders);

function updateStep(step: number): void {
  emit('update:step', step);
}

const conflictedBalanceSnapshot = ref<BalanceSnapshot | null>(null);

function checkAssetExist(asset: string): void {
  const assetFound = get(modelValue).balancesSnapshot.find((item: BalanceSnapshot) => item.assetIdentifier === asset);
  set(conflictedBalanceSnapshot, assetFound || null);
}

function closeConvertToEditDialog(): void {
  set(conflictedBalanceSnapshot, null);
}

function cancelConvertToEdit(): void {
  const currentFormModel = get(formModel);
  if (currentFormModel) {
    set(formModel, {
      ...currentFormModel,
      assetIdentifier: '',
    });
  }

  closeConvertToEditDialog();
}

function convertToEdit(): void {
  assert(conflictedBalanceSnapshot);
  const item = get(data).find(
    ({ assetIdentifier }) => assetIdentifier === get(conflictedBalanceSnapshot)?.assetIdentifier,
  );

  if (item)
    editClick(item);

  closeConvertToEditDialog();
}

function editClick(item: IndexedBalanceSnapshot): void {
  set(indexToEdit, item.index);

  const convertedFiatValue
    = get(currencySymbol) === CURRENCY_USD
      ? item.usdValue.toFixed()
      : item.usdValue.multipliedBy(get(fiatExchangeRate)).toFixed();

  set(formModel, {
    ...item,
    amount: item.amount.toFixed(),
    location: '',
    usdValue: convertedFiatValue,
  });

  set(openDialog, true);
}

const existingLocations = computed<string[]>(() =>
  get(modelValue).locationDataSnapshot.filter(item => item.location !== 'total').map(item => item.location),
);

function deleteClick(item: IndexedBalanceSnapshot): void {
  set(indexToDelete, item.index);
  set(showDeleteConfirmation, true);
  set(locationToDelete, '');
}

function add(): void {
  set(indexToEdit, null);
  set(formModel, {
    amount: '',
    assetIdentifier: '',
    category: BalanceType.ASSET,
    location: '',
    timestamp: get(timestamp),
    usdValue: '',
  });
  set(openDialog, true);
}

const previewLocationBalance = computed<Record<string, BigNumber> | null>(() => {
  const formVal = get(formModel);

  if (!formVal?.amount || !formVal.usdValue || !formVal.location)
    return null;

  const index = get(indexToEdit);
  const val = get(modelValue);

  const locationData = val.locationDataSnapshot.find(item => item.location === formVal.location);

  const usdValueInBigNumber = bigNumberify(formVal.usdValue);
  const convertedUsdValue
    = get(currencySymbol) === CURRENCY_USD ? usdValueInBigNumber : usdValueInBigNumber.dividedBy(get(fiatExchangeRate));

  if (!locationData) {
    return {
      after: convertedUsdValue,
      before: Zero,
    };
  }

  const isCurrentLiability = formVal.category === 'liability';
  const currentFactor = bigNumberify(isCurrentLiability ? -1 : 1);
  let usdValueDiff = convertedUsdValue.multipliedBy(currentFactor);

  const balancesSnapshot = val.balancesSnapshot;

  if (index !== null) {
    const isPrevLiability = balancesSnapshot[index].category === 'liability';
    const prevFactor = bigNumberify(isPrevLiability ? -1 : 1);
    usdValueDiff = usdValueDiff.minus(balancesSnapshot[index].usdValue.multipliedBy(prevFactor));
  }

  return {
    after: locationData.usdValue.plus(usdValueDiff),
    before: locationData.usdValue,
  };
});

const previewDeleteLocationBalance = computed<Record<string, BigNumber> | null>(() => {
  const index = get(indexToDelete);
  const location = get(locationToDelete);

  if (index === null || !location)
    return null;

  const val = get(modelValue);
  const locationData = val.locationDataSnapshot.find(item => item.location === location);
  const balanceData = val.balancesSnapshot[index];

  if (!locationData || !balanceData)
    return null;

  const isCurrentLiability = balanceData.category === 'liability';
  const currentFactor = bigNumberify(isCurrentLiability ? 1 : -1);
  const usdValueDiff = balanceData.usdValue.multipliedBy(currentFactor);

  return {
    after: locationData.usdValue.plus(usdValueDiff),
    before: locationData.usdValue,
  };
});

function updateData(
  balancesSnapshot: BalanceSnapshot[],
  location = '',
  calculatedBalance: Record<string, BigNumber> | null = null,
): void {
  const val = get(modelValue);
  const locationDataSnapshot = [...val.locationDataSnapshot];

  if (location) {
    const locationDataIndex = locationDataSnapshot.findIndex(item => item.location === location);
    if (locationDataIndex > -1) {
      locationDataSnapshot[locationDataIndex].usdValue = calculatedBalance!.after;
    }
    else {
      locationDataSnapshot.push({
        location,
        timestamp: get(timestamp),
        usdValue: calculatedBalance!.after,
      });
    }
  }

  const assetsValue = balancesSnapshot.map((item: BalanceSnapshot) => {
    if (item.category === 'asset')
      return item.usdValue;

    return item.usdValue.negated();
  });

  const totalValue = bigNumberSum(assetsValue);

  const totalDataIndex = locationDataSnapshot.findIndex(item => item.location === 'total');

  locationDataSnapshot[totalDataIndex].usdValue = totalValue;

  set(modelValue, {
    balancesSnapshot,
    locationDataSnapshot,
  });
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
  const index = get(indexToEdit);
  const val = get(modelValue);
  const timestampVal = get(timestamp);

  const balancesSnapshot = [...val.balancesSnapshot];
  const payload = {
    amount: bigNumberify(formData.amount),
    assetIdentifier: formData.assetIdentifier,
    category: formData.category,
    timestamp: timestampVal,
    usdValue: bigNumberify(formData.usdValue),
  };

  if (index !== null)
    balancesSnapshot[index] = payload;
  else balancesSnapshot.unshift(payload);

  set(submitting, false);

  updateData(balancesSnapshot, formData.location, get(previewLocationBalance));
  formRef?.submitPrice();
  clearEditDialog();
  return true;
}

function clearEditDialog(): void {
  set(openDialog, false);
  set(indexToEdit, null);
  set(formModel, null);
}

function clearDeleteDialog(): void {
  set(indexToDelete, null);
  set(showDeleteConfirmation, false);
  set(locationToDelete, '');
}

function confirmDelete(): void {
  const index = get(indexToDelete);
  const val = get(modelValue);
  const location = get(locationToDelete);

  if (index === null)
    return;

  const balancesSnapshot = [...val.balancesSnapshot];
  balancesSnapshot.splice(index, 1);

  updateData(balancesSnapshot, location, get(previewDeleteLocationBalance));
  clearDeleteDialog();
}
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 p-4 border-b border-default">
      <AssetSelect
        v-model="assetSearch"
        outlined
        hide-details
        clearable
        :label="t('dashboard.snapshot.search_asset')"
      />
    </div>
    <RuiDataTable
      ref="tableRef"
      v-model:sort="sort"
      class="table-inside-dialog !max-h-[calc(100vh-26.25rem)]"
      :cols="tableHeaders"
      :rows="filteredData"
      :scroller="tableRef?.$el"
      row-attr="assetIdentifier"
      dense
    >
      <template #item.categoryLabel="{ row }">
        <span>{{ toSentenceCase(row.categoryLabel) }}</span>
      </template>

      <template #item.assetIdentifier="{ row }">
        <AssetDetails
          v-if="!isNft(row.assetIdentifier)"
          class="[&_.avatar]:ml-1.5 [&_.avatar]:mr-2"
          :asset="row.assetIdentifier"
          :enable-association="false"
        />
        <NftDetails
          v-else
          :identifier="row.assetIdentifier"
        />
      </template>

      <template #item.amount="{ row }">
        <AmountDisplay :value="row.amount" />
      </template>

      <template #item.usdValue="{ row }">
        <AmountDisplay
          :value="row.usdValue"
          :amount="row.amount"
          :price-asset="row.assetIdentifier"
          :fiat-currency="CURRENCY_USD"
          :timestamp="timestamp"
        />
      </template>

      <template #item.action="{ row }">
        <RowActions
          :edit-tooltip="t('dashboard.snapshot.edit.dialog.actions.edit_item')"
          :delete-tooltip="t('dashboard.snapshot.edit.dialog.actions.delete_item')"
          @edit-click="editClick(row)"
          @delete-click="deleteClick(row)"
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
          color="primary"
          @click="updateStep(2)"
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
        indexToEdit !== null
          ? t('dashboard.snapshot.edit.dialog.balances.edit_title')
          : t('dashboard.snapshot.edit.dialog.balances.add_title')
      "
      :primary-action="t('common.actions.save')"
      :loading="submitting"
      :prompt-on-close="stateUpdated"
      @confirm="save()"
      @cancel="clearEditDialog()"
    >
      <EditBalancesSnapshotForm
        v-if="formModel"
        ref="form"
        v-model="formModel"
        v-model:state-updated="stateUpdated"
        :edit="!!indexToEdit"
        :preview-location-balance="previewLocationBalance"
        :locations="indexToEdit !== null ? existingLocations : []"
        :timestamp="timestamp"
        @update:asset="checkAssetExist($event)"
      />

      <ConfirmSnapshotConflictReplacementDialog
        :snapshot="conflictedBalanceSnapshot"
        @cancel="cancelConvertToEdit()"
        @confirm="convertToEdit()"
      />
    </BigDialog>

    <ConfirmDialog
      :display="showDeleteConfirmation"
      :title="t('dashboard.snapshot.edit.dialog.balances.delete_title')"
      :message="t('dashboard.snapshot.edit.dialog.balances.delete_confirmation')"
      max-width="700"
      @cancel="clearDeleteDialog()"
      @confirm="confirmDelete()"
    >
      <div class="mt-4">
        <EditBalancesSnapshotLocationSelector
          v-model="locationToDelete"
          :locations="existingLocations"
          :preview-location-balance="previewDeleteLocationBalance"
        />
      </div>
    </ConfirmDialog>
  </div>
</template>
