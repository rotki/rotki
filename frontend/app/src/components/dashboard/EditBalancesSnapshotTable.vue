<template>
  <div>
    <data-table
      ref="tableRef"
      class="table-inside-dialog"
      :headers="tableHeaders"
      :items="data"
      :container="tableContainer"
      :mobile-breakpoint="0"
    >
      <template #item.category="{ item }">
        <div>
          <span>{{ toSentenceCase(item.category) }}</span>
          <span v-if="isNft(item.assetIdentifier)">
            ({{ tc('dashboard.snapshot.edit.dialog.balances.nft') }})
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
          :edit-tooltip="tc('dashboard.snapshot.edit.dialog.actions.edit_item')"
          :delete-tooltip="
            tc('dashboard.snapshot.edit.dialog.actions.delete_item')
          "
          @edit-click="editClick(item)"
          @delete-click="deleteClick(item)"
        />
      </template>
    </data-table>
    <v-sheet elevation="10" class="d-flex align-center px-4 py-2">
      <div>
        <div class="text-caption">{{ tc('common.total') }}:</div>
        <div class="font-weight-bold text-h6 mt-n1">
          <amount-display :value="total" fiat-currency="USD" />
        </div>
      </div>
      <v-spacer />
      <v-btn text color="primary" class="mr-4" @click="add">
        <v-icon class="mr-2">mdi-plus</v-icon>
        <span>
          {{ tc('dashboard.snapshot.edit.dialog.actions.add_new_entry') }}
        </span>
      </v-btn>
      <v-btn color="primary" @click="updateStep(2)">
        {{ tc('common.actions.next') }}
      </v-btn>
    </v-sheet>

    <big-dialog
      :display="showForm"
      :title="
        indexToEdit !== null
          ? tc('dashboard.snapshot.edit.dialog.balances.edit_title')
          : tc('dashboard.snapshot.edit.dialog.balances.add_title')
      "
      :primary-action="tc('common.actions.save')"
      :action-disabled="loading || !valid"
      @confirm="save"
      @cancel="clearEditDialog"
    >
      <edit-balances-snapshot-form
        v-if="form"
        v-model="valid"
        :form="form"
        :excluded-assets="excludedAssets"
        :preview-location-balance="previewLocationBalance"
        :locations="indexToEdit !== null ? existingLocations : []"
        @update:form="updateForm"
      />
    </big-dialog>

    <confirm-dialog
      :display="showDeleteConfirmation"
      :title="tc('dashboard.snapshot.edit.dialog.balances.delete_title')"
      :message="
        tc('dashboard.snapshot.edit.dialog.balances.delete_confirmation')
      "
      max-width="700"
      @cancel="clearDeleteDialog"
      @confirm="confirmDelete"
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
<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { PropType } from 'vue';
import { DataTableHeader } from 'vuetify';
import EditBalancesSnapshotForm from '@/components/dashboard/EditBalancesSnapshotForm.vue';
import EditBalancesSnapshotLocationSelector from '@/components/dashboard/EditBalancesSnapshotLocationSelector.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { bigNumberSum } from '@/filters';
import { BalanceType } from '@/services/balances/types';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';
import {
  BalanceSnapshot,
  BalanceSnapshotPayload,
  Snapshot
} from '@/types/snapshots';
import { bigNumberify, One, sortDesc, Zero } from '@/utils/bignumbers';
import { isNft } from '@/utils/nft';
import { toSentenceCase } from '@/utils/text';

type IndexedBalanceSnapshot = BalanceSnapshot & { index: number };

const props = defineProps({
  value: {
    required: true,
    type: Object as PropType<Snapshot>
  },
  timestamp: {
    required: true,
    type: Number
  }
});

const emit = defineEmits(['update:step', 'input']);
const css = useCssModule();

const { value, timestamp } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const showForm = ref<boolean>(false);
const showDeleteConfirmation = ref<boolean>(false);
const indexToEdit = ref<number | null>(null);
const indexToDelete = ref<number | null>(null);
const locationToDelete = ref<string>('');
const form = ref<(BalanceSnapshotPayload & { location: string }) | null>(null);
const valid = ref<boolean>(false);
const loading = ref<boolean>(false);
const excludedAssets = ref<string[]>([]);

const { exchangeRate } = useBalancePricesStore();
const { tc } = useI18n();
const fiatExchangeRate = computed<BigNumber>(() => {
  return get(exchangeRate(get(currencySymbol))) ?? One;
});

const data = computed<IndexedBalanceSnapshot[]>(() => {
  return get(value).balancesSnapshot.map((item, index) => ({
    ...item,
    index
  }));
});

const total = computed<BigNumber>(() => {
  const totalEntry = get(value).locationDataSnapshot.find(
    item => item.location === 'total'
  );

  if (!totalEntry) return Zero;
  return totalEntry.usdValue;
});

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: tc('common.category'),
    value: 'category',
    cellClass: 'py-2',
    width: 150
  },
  {
    text: tc('common.asset'),
    value: 'assetIdentifier'
  },
  {
    text: tc('common.amount'),
    value: 'amount',
    align: 'end',
    sort: (a: BigNumber, b: BigNumber) => sortDesc(a, b)
  },
  {
    text: tc('common.value_in_symbol', 0, {
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

  set(
    excludedAssets,
    get(value)
      .balancesSnapshot.map(item => item.assetIdentifier)
      .filter(identifier => identifier !== item.assetIdentifier)
  );

  set(showForm, true);
};

const existingLocations = computed<string[]>(() => {
  return get(value)
    .locationDataSnapshot.filter(item => item.location !== 'total')
    .map(item => item.location);
});

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
  set(
    excludedAssets,
    get(value).balancesSnapshot.map(item => item.assetIdentifier)
  );
  set(showForm, true);
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

    const convertedUsdValue =
      get(currencySymbol) === CURRENCY_USD
        ? bigNumberify(formVal.usdValue)
        : bigNumberify(formVal.usdValue).dividedBy(get(fiatExchangeRate));

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

    if (!locationData || !balanceData) return null;

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
  location: string = '',
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
    if (item.category === 'asset') return item.usdValue;
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

const save = () => {
  const formVal = get(form);

  if (!formVal) return;
  const index = get(indexToEdit);
  const val = get(value);
  const timestampVal = get(timestamp);

  const convertedUsdValue =
    get(currencySymbol) === CURRENCY_USD
      ? bigNumberify(formVal.usdValue)
      : bigNumberify(formVal.usdValue).dividedBy(get(fiatExchangeRate));

  let balancesSnapshot = [...val.balancesSnapshot];
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

const clearEditDialog = () => {
  set(indexToEdit, null);
  set(showForm, false);
  set(form, null);
  set(excludedAssets, []);
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

  if (index === null) return;

  let balancesSnapshot = [...val.balancesSnapshot];
  balancesSnapshot.splice(index, 1);

  updateData(balancesSnapshot, location, get(previewDeleteLocationBalance));
  clearDeleteDialog();
};

const tableRef = ref<any>(null);

const tableContainer = computed(() => {
  return get(tableRef)?.$el;
});
</script>
<style module lang="scss">
.asset {
  max-width: 640px;
}
</style>
