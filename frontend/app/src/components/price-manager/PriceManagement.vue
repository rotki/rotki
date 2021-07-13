<template>
  <v-container>
    <v-row justify="space-between" align="center" no-gutters class="mt-8">
      <v-col>
        <card-title>{{ $t('price_management.title') }}</card-title>
      </v-col>
    </v-row>
    <card class="mt-8">
      <template #title>{{ $t('price_management.filter_title') }}</template>
      <v-row>
        <v-col cols="12" md="6">
          <asset-select
            v-model="filter.fromAsset"
            outlined
            :label="$t('price_management.from_asset')"
            clearable
          />
        </v-col>
        <v-col cols="12" md="6">
          <asset-select
            v-model="filter.toAsset"
            outlined
            :label="$t('price_management.to_asset')"
            clearable
          />
        </v-col>
      </v-row>
    </card>
    <price-table
      class="mt-12"
      :filter="filter"
      :refresh="refresh"
      @edit="openForm($event)"
      @refreshed="refresh = false"
    >
      <v-btn absolute fab top right color="primary" @click="openForm()">
        <v-icon> mdi-plus </v-icon>
      </v-btn>
    </price-table>
    <big-dialog
      :display="showForm"
      :title="
        editMode
          ? $t('price_management.dialog.edit_title')
          : $t('price_management.dialog.add_title')
      "
      :action-disabled="!valid"
      @confirm="managePrice(price, editMode)"
      @cancel="hideForm()"
    >
      <price-form v-model="price" :edit="editMode" @valid="valid = $event" />
    </big-dialog>
  </v-container>
</template>

<script lang="ts">
import {
  defineComponent,
  inject,
  reactive,
  Ref,
  ref
} from '@vue/composition-api';
import { Store } from 'vuex';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import PriceForm from '@/components/price-manager/PriceFrom.vue';
import PriceTable from '@/components/price-manager/PriceTable.vue';
import i18n from '@/i18n';
import { HistoricalPrice } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { Message, RotkehlchenState } from '@/store/types';
import { Nullable } from '@/types';
import { assert } from '@/utils/assertions';
import { Zero } from '@/utils/bignumbers';

const emptyPrice: () => HistoricalPrice = () => ({
  fromAsset: '',
  toAsset: '',
  price: Zero,
  timestamp: 0
});

const managePrice = (
  showForm: Ref<Boolean>,
  refresh: Ref<Boolean>,
  store: Store<RotkehlchenState>
) => {
  const managePrice = async (price: HistoricalPrice, edit: boolean) => {
    try {
      if (edit) {
        await api.assets.editHistoricalPrice(price);
      } else {
        await api.assets.addHistoricalPrice(price);
      }

      showForm.value = false;
      if (!refresh.value) {
        refresh.value = true;
      }
    } catch (e) {
      const values = { message: e.message };
      const title = edit
        ? i18n.t('price_management.edit.error.title')
        : i18n.t('price_management.add.error.title');
      const description = edit
        ? i18n.t('price_management.edit.error.description', values)
        : i18n.t('price_management.add.error.description', values);
      const message: Message = {
        title: title.toString(),
        description: description.toString(),
        success: false
      };
      store.commit('setMessage', message);
    }
  };

  return {
    managePrice
  };
};

export default defineComponent({
  name: 'PriceManagement',
  components: { PriceTable, PriceForm, BigDialog },
  setup() {
    const store = inject<Store<RotkehlchenState>>('vuex-store');
    assert(store);
    const refresh = ref(false);
    const price = ref(emptyPrice());
    const showForm = ref(false);
    const filter = reactive<{
      fromAsset: Nullable<string>;
      toAsset: Nullable<string>;
    }>({
      fromAsset: null,
      toAsset: null
    });
    const valid = ref(false);
    const editMode = ref(false);

    const openForm = function (hPrice: HistoricalPrice = emptyPrice()) {
      editMode.value = !!hPrice.timestamp;
      price.value = editMode.value
        ? hPrice
        : {
            ...hPrice,
            fromAsset: filter.fromAsset ?? '',
            toAsset: filter.toAsset ?? ''
          };
      showForm.value = true;
    };

    const hideForm = function () {
      showForm.value = false;
      price.value = emptyPrice();
    };

    return {
      ...managePrice(showForm, refresh, store),
      refresh,
      filter,
      openForm,
      hideForm,
      showForm,
      editMode,
      price,
      valid
    };
  }
});
</script>

<style scoped></style>
