<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { type ComputedRef, type Ref } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { CURRENCY_USD } from '@/types/currencies';
import {
  type BalanceSnapshot,
  type BalanceSnapshotPayload,
  type Snapshot
} from '@/types/snapshots';
import { isNft } from '@/utils/nft';
import { toSentenceCase } from '@/utils/text';
import { BalanceType } from '@/types/balances';

const { t } = useI18n();

type IndexedBalanceSnapshot = BalanceSnapshot & { index: number };

const props = defineProps<{
  value: Snapshot;
  timestamp: number;
}>();

const emit = defineEmits<{
  (e: 'update:step', step: number): void;
  (e: 'input', value: Snapshot): void;
}>();

const css = useCssModule();

const { value, timestamp } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const showDeleteConfirmation = ref<boolean>(false);
const indexToEdit = ref<number | null>(null);
const indexToDelete = ref<number | null>(null);
const locationToDelete = ref<string>('');
const form = ref<(BalanceSnapshotPayload & { location: string }) | null>(null);

const { exchangeRate } = useBalancePricesStore();
const fiatExchangeRate = computed<BigNumber>(
  () => get(exchangeRate(get(currencySymbol))) ?? One
);

const data: ComputedRef<IndexedBalanceSnapshot[]> = computed(() =>
  get(value).balancesSnapshot.map((item, index) => ({
    ...item,
    index
  }))
);

const assetSearch: Ref<string> = ref('');
const filteredData: ComputedRef<IndexedBalanceSnapshot[]> = computed(() => {
  const allData = get(data);
  const search = get(assetSearch);
  if (!search) {
    return allData;
  }
  return allData.filter(({ assetIdentifier }) => assetIdentifier === search);
});

const total = computed<BigNumber>(() => {
  const totalEntry = get(value).locationDataSnapshot.find(
    item => item.location === 'total'
  );

  if (!totalEntry) {
    return Zero;
  }
  return totalEntry.usdValue;
});

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.category'),
    value: 'category',
    cellClass: 'py-2',
    width: 150
  },
  {
    text: t('common.asset'),
    value: 'assetIdentifier'
  },
  {
    text: t('common.amount'),
    value: 'amount',
    align: 'end',
    sort: (a: BigNumber, b: BigNumber) => sortDesc(a, b)
  },
  {
    text: t('common.value_in_symbol', {
      symbol: get(currencySymbol)
    }).toString(),
    value: 'usdValue',
    align: 'end',
    sort: (a: BigNumber, b: BigNumber) => sortDesc(a, b)
  },
  {
    text: '',
    value: 'action',
    cellClass: 'py-2',
    width: 100,
    sortable: false
  }
]);

const input = (value: Snapshot) => {
  emit('input', value);
};

const updateStep = (step: number) => {
  emit('update:step', step);
};

const conflictedBalanceSnapshot: Ref<BalanceSnapshot | null> = ref(null);
const checkAssetExist = (asset: string) => {
  const assetFound = get(value).balancesSnapshot.find(
    item => item.assetIdentifier === asset
  );
  set(conflictedBalanceSnapshot, assetFound || null);
};

const closeConvertToEditDialog = () => {
  set(conflictedBalanceSnapshot, null);
};

const cancelConvertToEdit = () => {
  set(form, {
    ...get(form),
    assetIdentifier: ''
  });

  closeConvertToEditDialog();
};
const convertToEdit = () => {
  assert(conflictedBalanceSnapshot);
  const item = get(data).find(
    ({ assetIdentifier }) =>
      assetIdentifier === get(conflictedBalanceSnapshot)?.assetIdentifier
  );

  if (item) {
    editClick(item);
  }
  closeConvertToEditDialog();
};

const editClick = (item: IndexedBalanceSnapshot) => {
  set(indexToEdit, item.index);

  const convertedFiatValue =
    get(currencySymbol) === CURRENCY_USD
      ? item.usdValue.toFixed()
      : item.usdValue.multipliedBy(get(fiatExchangeRate)).toFixed();

  set(form, {
    ...item,
    amount: item.amount.toFixed(),
    usdValue: convertedFiatValue,
    location: ''
  });

  setOpenDialog(true);
};

const existingLocations = computed<string[]>(() =>
  get(value)
    .locationDataSnapshot.filter(item => item.location !== 'total')
    .map(item => item.location)
);

const deleteClick = (item: IndexedBalanceSnapshot) => {
  set(indexToDelete, item.index);
  set(showDeleteConfirmation, true);
  set(locationToDelete, '');
};

const add = () => {
  set(indexToEdit, null);
  set(form, {
    timestamp: get(timestamp),
    category: BalanceType.ASSET,
    assetIdentifier: '',
    amount: '',
    usdValue: '',
    location: ''
  });
  setOpenDialog(true);
};

const previewLocationBalance = computed<Record<string, BigNumber> | null>(
  () => {
    const formVal = get(form);

    if (!formVal || !formVal.amount || !formVal.usdValue || !formVal.location) {
      return null;
    }

    const index = get(indexToEdit);
    const val = get(value);

    const locationData = val.locationDataSnapshot.find(
      item => item.location === formVal.location
    );

    const usdValueInBigNumber = bigNumberify(formVal.usdValue);
    const convertedUsdValue =
      get(currencySymbol) === CURRENCY_USD
        ? usdValueInBigNumber
        : usdValueInBigNumber.dividedBy(get(fiatExchangeRate));

    if (!locationData) {
      return {
        before: Zero,
        after: convertedUsdValue
      };
    }

    const isCurrentLiability = formVal.category === 'liability';
    const currentFactor = bigNumberify(isCurrentLiability ? -1 : 1);
    let usdValueDiff = convertedUsdValue.multipliedBy(currentFactor);

    const balancesSnapshot = val.balancesSnapshot;

    if (index !== null) {
      const isPrevLiability = balancesSnapshot[index].category === 'liability';
      const prevFactor = bigNumberify(isPrevLiability ? -1 : 1);
      usdValueDiff = usdValueDiff.minus(
        balancesSnapshot[index].usdValue.multipliedBy(prevFactor)
      );
    }

    return {
      before: locationData.usdValue,
      after: locationData.usdValue.plus(usdValueDiff)
    };
  }
);

const previewDeleteLocationBalance = computed<Record<string, BigNumber> | null>(
  () => {
    const index = get(indexToDelete);
    const location = get(locationToDelete);

    if (index === null || !location) {
      return null;
    }

    const val = get(value);
    const locationData = val.locationDataSnapshot.find(
      item => item.location === location
    );
    const balanceData = val.balancesSnapshot[index];

    if (!locationData || !balanceData) {
      return null;
    }

    const isCurrentLiability = balanceData.category === 'liability';
    const currentFactor = bigNumberify(isCurrentLiability ? 1 : -1);
    const usdValueDiff = balanceData.usdValue.multipliedBy(currentFactor);

    return {
      before: locationData.usdValue,
      after: locationData.usdValue.plus(usdValueDiff)
    };
  }
);

const updateData = (
  balancesSnapshot: BalanceSnapshot[],
  location = '',
  calculatedBalance: Record<string, BigNumber> | null = null
) => {
  const val = get(value);
  const locationDataSnapshot = [...val.locationDataSnapshot];

  if (location) {
    const locationDataIndex = locationDataSnapshot.findIndex(
      item => item.location === location
    );
    if (locationDataIndex > -1) {
      locationDataSnapshot[locationDataIndex].usdValue =
        calculatedBalance!.after;
    } else {
      locationDataSnapshot.push({
        timestamp: get(timestamp),
        location,
        usdValue: calculatedBalance!.after
      });
    }
  }

  const assetsValue = balancesSnapshot.map((item: BalanceSnapshot) => {
    if (item.category === 'asset') {
      return item.usdValue;
    }
    return item.usdValue.negated();
  });

  const total = bigNumberSum(assetsValue);

  const totalDataIndex = locationDataSnapshot.findIndex(
    item => item.location === 'total'
  );

  locationDataSnapshot[totalDataIndex].usdValue = total;

  input({
    balancesSnapshot,
    locationDataSnapshot
  });
};

const {
  openDialog,
  setOpenDialog,
  closeDialog,
  submitting,
  setSubmitFunc,
  trySubmit
} = useEditBalancesSnapshotForm();

const save = async () => {
  const formVal = get(form);

  if (!formVal) {
    return;
  }
  const index = get(indexToEdit);
  const val = get(value);
  const timestampVal = get(timestamp);

  const usdValueInBigNumber = bigNumberify(formVal.usdValue);
  const convertedUsdValue =
    get(currencySymbol) === CURRENCY_USD
      ? usdValueInBigNumber
      : usdValueInBigNumber.dividedBy(get(fiatExchangeRate));

  const balancesSnapshot = [...val.balancesSnapshot];
  const payload = {
    timestamp: timestampVal,
    category: formVal.category,
    assetIdentifier: formVal.assetIdentifier,
    amount: bigNumberify(formVal.amount),
    usdValue: convertedUsdValue
  };

  if (index !== null) {
    balancesSnapshot[index] = payload;
  } else {
    balancesSnapshot.unshift(payload);
  }

  updateData(balancesSnapshot, formVal.location, get(previewLocationBalance));
  clearEditDialog();
};

setSubmitFunc(save);

const clearEditDialog = () => {
  closeDialog();
  set(indexToEdit, null);
  set(form, null);
};

const updateForm = (newForm: BalanceSnapshotPayload & { location: string }) => {
  set(form, newForm);
};

const clearDeleteDialog = () => {
  set(indexToDelete, null);
  set(showDeleteConfirmation, false);
  set(locationToDelete, '');
};

const confirmDelete = () => {
  const index = get(indexToDelete);
  const val = get(value);
  const location = get(locationToDelete);

  if (index === null) {
    return;
  }

  const balancesSnapshot = [...val.balancesSnapshot];
  balancesSnapshot.splice(index, 1);

  updateData(balancesSnapshot, location, get(previewDeleteLocationBalance));
  clearDeleteDialog();
};

const tableRef = ref<any>(null);

const tableContainer = computed(() => get(tableRef)?.$el);
</script>

<template>
  <div>
    <v-row class="pa-4">
      <v-col md="6">
        <asset-select
          v-model="assetSearch"
          outlined
          hide-details
          clearable
          :label="t('dashboard.snapshot.search_asset')"
        />
      </v-col>
    </v-row>
    <data-table
      ref="tableRef"
      class="table-inside-dialog"
      :class="css['table-inside-dialog']"
      :headers="tableHeaders"
      :items="filteredData"
      :container="tableContainer"
      :mobile-breakpoint="0"
    >
      <template #item.category="{ item }">
        <div>
          <span>{{ toSentenceCase(item.category) }}</span>
          <span v-if="isNft(item.assetIdentifier)">
            ({{ t('dashboard.snapshot.edit.dialog.balances.nft') }})
          </span>
        </div>
      </template>

      <template #item.assetIdentifier="{ item }">
        <asset-details
          v-if="!isNft(item.assetIdentifier)"
          :class="css.asset"
          :asset-styled="{ padding: '2px 0.75rem' }"
          :asset="item.assetIdentifier"
          :opens-details="false"
          :enable-association="false"
        />
        <div v-else>
          <nft-details :identifier="item.assetIdentifier" :class="css.asset" />
        </div>
      </template>

      <template #item.amount="{ item }">
        <amount-display :value="item.amount" />
      </template>

      <template #item.usdValue="{ item }">
        <amount-display :value="item.usdValue" fiat-currency="USD" />
      </template>

      <template #item.action="{ item }">
        <row-actions
          :edit-tooltip="t('dashboard.snapshot.edit.dialog.actions.edit_item')"
          :delete-tooltip="
            t('dashboard.snapshot.edit.dialog.actions.delete_item')
          "
          @edit-click="editClick(item)"
          @delete-click="deleteClick(item)"
        />
      </template>
    </data-table>
    <v-sheet elevation="10" class="d-flex align-center px-4 py-2">
      <div>
        <div class="text-caption">{{ t('common.total') }}:</div>
        <div class="font-weight-bold text-h6 mt-n1">
          <amount-display :value="total" fiat-currency="USD" />
        </div>
      </div>
      <v-spacer />
      <v-btn text color="primary" class="mr-4" @click="add()">
        <v-icon class="mr-2">mdi-plus</v-icon>
        <span>
          {{ t('dashboard.snapshot.edit.dialog.actions.add_new_entry') }}
        </span>
      </v-btn>
      <v-btn color="primary" @click="updateStep(2)">
        {{ t('common.actions.next') }}
      </v-btn>
    </v-sheet>

    <big-dialog
      :display="openDialog"
      :title="
        indexToEdit !== null
          ? t('dashboard.snapshot.edit.dialog.balances.edit_title')
          : t('dashboard.snapshot.edit.dialog.balances.add_title')
      "
      :primary-action="t('common.actions.save')"
      :loading="submitting"
      @confirm="trySubmit()"
      @cancel="clearEditDialog()"
    >
      <edit-balances-snapshot-form
        v-if="form"
        :edit="!!indexToEdit"
        :form="form"
        :preview-location-balance="previewLocationBalance"
        :locations="indexToEdit !== null ? existingLocations : []"
        @update:form="updateForm($event)"
        @update:asset="checkAssetExist($event)"
      />

      <confirm-snapshot-conflict-replacement-dialog
        :snapshot="conflictedBalanceSnapshot"
        @cancel="cancelConvertToEdit()"
        @confirm="convertToEdit()"
      />
    </big-dialog>

    <confirm-dialog
      :display="showDeleteConfirmation"
      :title="t('dashboard.snapshot.edit.dialog.balances.delete_title')"
      :message="
        t('dashboard.snapshot.edit.dialog.balances.delete_confirmation')
      "
      max-width="700"
      @cancel="clearDeleteDialog()"
      @confirm="confirmDelete()"
    >
      <div class="mt-4">
        <edit-balances-snapshot-location-selector
          v-model="locationToDelete"
          :locations="existingLocations"
          :preview-location-balance="previewDeleteLocationBalance"
        />
      </div>
    </confirm-dialog>
  </div>
</template>

<style module lang="scss">
.asset {
  max-width: 640px;
}

.table-inside-dialog {
  max-height: calc(100vh - 420px);
}
</style>
