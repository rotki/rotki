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
          <nft-details :identifier="item.assetIdentifier" />
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
    <v-sheet elevation="10" class="d-flex justify-end pa-4">
      <v-btn color="primary" @click="add">
        <v-icon class="mr-2">mdi-plus-circle</v-icon>
        <span>
          {{ $t('dashboard.snapshot.edit.dialog.actions.add_new_entry') }}
        </span>
      </v-btn>
      <v-spacer />
      <v-btn color="primary" @click="updateStep(2)">
        {{ $t('dashboard.snapshot.edit.dialog.actions.next') }}
        <v-icon>mdi-chevron-right</v-icon>
      </v-btn>
    </v-sheet>

    <big-dialog
      :display="showForm"
      :title="
        editedIndex !== null
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
        @update:form="updateForm"
      />
    </big-dialog>

    <confirm-dialog
      :display="showDeleteConfirmation"
      :title="$t('dashboard.snapshot.edit.dialog.balances.delete_title')"
      :message="
        $t('dashboard.snapshot.edit.dialog.balances.delete_confirmation')
      "
      @cancel="clearDeleteDialog"
      @confirm="confirmDelete"
    />
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
import BigDialog from '@/components/dialogs/BigDialog.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { setupExchangeRateGetter } from '@/composables/balances';
import { setupGeneralSettings } from '@/composables/session';
import { CURRENCY_USD } from '@/data/currencies';
import i18n from '@/i18n';
import {
  BalanceSnapshot,
  BalanceSnapshotPayload
} from '@/store/balances/types';
import { bigNumberify, One } from '@/utils/bignumbers';
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
        align: 'end'
      },
      {
        text: i18n
          .t('dashboard.snapshot.edit.dialog.balances.headers.value', {
            currency: get(currency)
          })
          .toString(),
        value: 'usdValue',
        align: 'end'
      },
      {
        text: '',
        value: 'action',
        cellClass: 'py-2',
        width: 100
      }
    ];
  });

export default defineComponent({
  name: 'EditBalancesSnapshotTable',
  components: { NftDetails, EditBalancesSnapshotForm, BigDialog, RowActions },
  props: {
    value: {
      required: true,
      type: Array as PropType<BalanceSnapshot[]>
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
    const editedIndex = ref<number | null>(null);
    const deletedIndex = ref<number | null>(null);
    const form = ref<BalanceSnapshotPayload | null>(null);
    const valid = ref<boolean>(false);
    const loading = ref<boolean>(false);
    const excludedAssets = ref<string[]>([]);

    const exchangeRate = setupExchangeRateGetter();
    const fiatExchangeRate = computed<BigNumber>(() => {
      return exchangeRate(get(currencySymbol)) ?? One;
    });

    const data = computed<IndexedBalanceSnapshot[]>(() => {
      return get(value).map((item, index) => ({ ...item, index }));
    });

    const input = (value: BalanceSnapshot[]) => {
      emit('input', value);
    };

    const updateStep = (step: number) => {
      emit('update:step', step);
    };

    const editClick = (item: IndexedBalanceSnapshot) => {
      set(editedIndex, item.index);

      const convertedFiatValue =
        get(currencySymbol) === CURRENCY_USD
          ? item.usdValue.toFixed()
          : item.usdValue.multipliedBy(get(fiatExchangeRate)).toFixed();

      set(form, {
        ...item,
        amount: item.amount.toFixed(),
        usdValue: convertedFiatValue
      });

      set(
        excludedAssets,
        get(value)
          .map(item => item.assetIdentifier)
          .filter(identifier => identifier !== item.assetIdentifier)
      );

      set(showForm, true);
    };

    const deleteClick = (item: IndexedBalanceSnapshot) => {
      set(deletedIndex, item.index);
      set(showDeleteConfirmation, true);
    };

    const add = () => {
      set(editedIndex, null);
      set(form, {
        timestamp: get(timestamp),
        category: 'asset',
        assetIdentifier: '',
        amount: '',
        usdValue: ''
      });
      set(
        excludedAssets,
        get(value).map(item => item.assetIdentifier)
      );
      set(showForm, true);
    };

    const save = () => {
      const formVal = get(form);

      if (!formVal) return;
      const index = get(editedIndex);
      const val = get(value);
      const timestampVal = get(timestamp);

      const convertedUsdValue =
        get(currencySymbol) === CURRENCY_USD
          ? bigNumberify(formVal.usdValue)
          : bigNumberify(formVal.usdValue).dividedBy(get(fiatExchangeRate));

      let newValue = [...val];
      const payload = {
        timestamp: timestampVal,
        category: formVal.category,
        assetIdentifier: formVal.assetIdentifier,
        amount: bigNumberify(formVal.amount),
        usdValue: convertedUsdValue
      };

      if (index !== null) {
        newValue[index] = payload;
      } else {
        newValue.unshift(payload);
      }

      input(newValue);
      clearEditDialog();
    };

    const clearEditDialog = () => {
      set(editedIndex, null);
      set(showForm, false);
      set(form, null);
      set(excludedAssets, []);
    };

    const updateForm = (newForm: BalanceSnapshotPayload) => {
      set(form, newForm);
    };

    const clearDeleteDialog = () => {
      set(deletedIndex, null);
      set(showDeleteConfirmation, false);
    };

    const confirmDelete = () => {
      const index = get(deletedIndex);
      const val = get(value);

      if (index === null) return;

      let newValue = [...val];
      newValue.splice(index, 1);

      input(newValue);
      clearDeleteDialog();
    };

    return {
      data,
      showForm,
      showDeleteConfirmation,
      editedIndex,
      form,
      tableHeaders: tableHeaders(currencySymbol),
      valid,
      loading,
      excludedAssets,
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
