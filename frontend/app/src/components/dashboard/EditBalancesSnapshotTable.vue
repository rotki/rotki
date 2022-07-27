<template>
  <div>
    <data-table
      :class="$style.table"
      :headers="tableHeaders"
      :items="data"
      :mobile-breakpoint="0"
    >
      <template #item.category="{ item }">
        <div>
          <span>{{ toSentenceCase(item.category) }}</span>
          <span v-if="isNft(item.assetIdentifier)">
            ({{ $t('dashboard.snapshot.edit.dialog.balances.nft') }})
          </span>
        </div>
      </template>

      <template #item.assetIdentifier="{ item }">
        <asset-details
          v-if="!isNft(item.assetIdentifier)"
          :class="$style.asset"
          :asset="item.assetIdentifier"
          :opens-details="false"
          :enable-association="false"
        />
        <div v-else>
          <nft-details
            :identifier="item.assetIdentifier"
            :class="$style.asset"
          />
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
          :edit-tooltip="$t('dashboard.snapshot.edit.dialog.actions.edit_item')"
          :delete-tooltip="
            $t('dashboard.snapshot.edit.dialog.actions.delete_item')
          "
          @edit-click="editClick(item)"
          @delete-click="deleteClick(item)"
        />
      </template>
    </data-table>
    <v-sheet elevation="10" class="d-flex align-center px-4 py-2">
      <div>
        <div class="text-caption">
          {{ $t('dashboard.snapshot.edit.dialog.total.title') }}:
        </div>
        <div class="font-weight-bold text-h6 mt-n1">
          <amount-display :value="total" fiat-currency="USD" />
        </div>
      </div>
      <v-spacer />
      <v-btn text color="primary" class="mr-4" @click="add">
        <v-icon class="mr-2">mdi-plus</v-icon>
        <span>
          {{ $t('dashboard.snapshot.edit.dialog.actions.add_new_entry') }}
        </span>
      </v-btn>
      <v-btn color="primary" @click="updateStep(2)">
        {{ $t('dashboard.snapshot.edit.dialog.actions.next') }}
      </v-btn>
    </v-sheet>

    <big-dialog
      :display="showForm"
      :title="
        indexToEdit !== null
          ? $t('dashboard.snapshot.edit.dialog.balances.edit_title')
          : $t('dashboard.snapshot.edit.dialog.balances.add_title')
      "
      :primary-action="$t('dashboard.snapshot.edit.dialog.actions.save')"
      :action-disabled="loading || !valid"
      @confirm="save"
      @cancel="clearEditDialog"
    >
      <edit-balances-snapshot-form
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
      :title="$t('dashboard.snapshot.edit.dialog.balances.delete_title')"
      :message="
        $t('dashboard.snapshot.edit.dialog.balances.delete_confirmation')
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
<script lang="ts">
import { BigNumber } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  Ref,
  ref,
  toRefs
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
import EditBalancesSnapshotForm from '@/components/dashboard/EditBalancesSnapshotForm.vue';
import EditBalancesSnapshotLocationSelector from '@/components/dashboard/EditBalancesSnapshotLocationSelector.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { setupExchangeRateGetter } from '@/composables/balances';
import { setupGeneralSettings } from '@/composables/session';
import { CURRENCY_USD } from '@/data/currencies';
import { bigNumberSum } from '@/filters';
import i18n from '@/i18n';
import {
  BalanceSnapshot,
  BalanceSnapshotPayload,
  Snapshot
} from '@/store/balances/types';
import { bigNumberify, One, sortDesc, Zero } from '@/utils/bignumbers';
import { isNft } from '@/utils/nft';
import { toSentenceCase } from '@/utils/text';

type IndexedBalanceSnapshot = BalanceSnapshot & { index: number };

const tableHeaders = (currency: Ref<string>) =>
  computed<DataTableHeader[]>(() => {
    return [
      {
        text: i18n
          .t('dashboard.snapshot.edit.dialog.balances.headers.category')
          .toString(),
        value: 'category',
        cellClass: 'py-2',
        width: 150
      },
      {
        text: i18n
          .t('dashboard.snapshot.edit.dialog.balances.headers.asset')
          .toString(),
        value: 'assetIdentifier'
      },
      {
        text: i18n
          .t('dashboard.snapshot.edit.dialog.balances.headers.amount')
          .toString(),
        value: 'amount',
        align: 'end',
        sort: (a: BigNumber, b: BigNumber) => sortDesc(a, b)
      },
      {
        text: i18n
          .t('dashboard.snapshot.edit.dialog.balances.headers.value', {
            currency: get(currency)
          })
          .toString(),
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
    ];
  });

export default defineComponent({
  name: 'EditBalancesSnapshotTable',
  components: {
    EditBalancesSnapshotLocationSelector,
    NftDetails,
    EditBalancesSnapshotForm,
    BigDialog,
    RowActions
  },
  props: {
    value: {
      required: true,
      type: Object as PropType<Snapshot>
    },
    timestamp: {
      required: true,
      type: Number
    }
  },
  emits: ['update:step', 'input'],
  setup(props, { emit }) {
    const { value, timestamp } = toRefs(props);
    const { currencySymbol } = setupGeneralSettings();
    const showForm = ref<boolean>(false);
    const showDeleteConfirmation = ref<boolean>(false);
    const indexToEdit = ref<number | null>(null);
    const indexToDelete = ref<number | null>(null);
    const locationToDelete = ref<string>('');
    const form = ref<(BalanceSnapshotPayload & { location: string }) | null>(
      null
    );
    const valid = ref<boolean>(false);
    const loading = ref<boolean>(false);
    const excludedAssets = ref<string[]>([]);

    const exchangeRate = setupExchangeRateGetter();
    const fiatExchangeRate = computed<BigNumber>(() => {
      return exchangeRate(get(currencySymbol)) ?? One;
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
          ? item.usdValue.toFormat()
          : item.usdValue.multipliedBy(get(fiatExchangeRate)).toFormat();

      set(form, {
        ...item,
        amount: item.amount.toFormat(),
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
        category: 'asset',
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

        if (
          !formVal ||
          !formVal.amount ||
          !formVal.usdValue ||
          !formVal.location
        ) {
          return null;
        }

        const index = get(indexToEdit);
        const val = get(value);

        const locationData = val.locationDataSnapshot.find(
          item => item.location === formVal.location
        );

        if (!locationData) return null;

        const convertedUsdValue =
          get(currencySymbol) === CURRENCY_USD
            ? bigNumberify(formVal.usdValue)
            : bigNumberify(formVal.usdValue).dividedBy(get(fiatExchangeRate));

        const isCurrentLiability = formVal.category === 'liability';
        const currentFactor = bigNumberify(isCurrentLiability ? -1 : 1);
        let usdValueDiff = convertedUsdValue.multipliedBy(currentFactor);

        const balancesSnapshot = val.balancesSnapshot;

        if (index !== null) {
          const isPrevLiability =
            balancesSnapshot[index].category === 'liability';
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

    const previewDeleteLocationBalance = computed<Record<
      string,
      BigNumber
    > | null>(() => {
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
    });

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

      updateData(
        balancesSnapshot,
        formVal.location,
        get(previewLocationBalance)
      );
      clearEditDialog();
    };

    const clearEditDialog = () => {
      set(indexToEdit, null);
      set(showForm, false);
      set(form, null);
      set(excludedAssets, []);
    };

    const updateForm = (
      newForm: BalanceSnapshotPayload & { location: string }
    ) => {
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

      if (index === null || !location) return;

      let balancesSnapshot = [...val.balancesSnapshot];
      balancesSnapshot.splice(index, 1);

      updateData(balancesSnapshot, location, get(previewDeleteLocationBalance));
      clearDeleteDialog();
    };

    return {
      data,
      showForm,
      showDeleteConfirmation,
      indexToEdit,
      form,
      tableHeaders: tableHeaders(currencySymbol),
      valid,
      loading,
      excludedAssets,
      total,
      existingLocations,
      locationToDelete,
      previewLocationBalance,
      previewDeleteLocationBalance,
      isNft,
      add,
      save,
      clearEditDialog,
      toSentenceCase,
      updateStep,
      editClick,
      deleteClick,
      updateForm,
      clearDeleteDialog,
      confirmDelete
    };
  }
});
</script>
<style module lang="scss">
.table {
  scroll-behavior: smooth;
  max-height: calc(100vh - 310px);
  overflow: auto;
}

.asset {
  max-width: 640px;
}
</style>
