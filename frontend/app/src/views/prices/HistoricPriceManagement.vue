<template>
  <v-container>
    <v-row justify="space-between" align="center" no-gutters>
      <v-col>
        <card-title>{{ tc('price_management.historic.title') }}</card-title>
      </v-col>
    </v-row>
    <card class="mt-8">
      <template #title>{{ tc('price_management.filter_title') }}</template>
      <v-row>
        <v-col cols="12" md="6">
          <asset-select
            v-model="filter.fromAsset"
            outlined
            :label="tc('price_management.from_asset')"
            clearable
            hide-details
          />
        </v-col>
        <v-col cols="12" md="6">
          <asset-select
            v-model="filter.toAsset"
            outlined
            :label="tc('price_management.to_asset')"
            clearable
            hide-details
          />
        </v-col>
      </v-row>
    </card>
    <historic-price-table
      class="mt-12"
      :filter="filter"
      :refreshing="refreshing"
      @edit="openForm($event)"
      @refreshed="refreshing = false"
    >
      <v-btn absolute fab top right color="primary" @click="openForm()">
        <v-icon> mdi-plus </v-icon>
      </v-btn>
    </historic-price-table>
    <big-dialog
      :display="showForm"
      :title="
        editMode
          ? tc('price_management.dialog.edit_title')
          : tc('price_management.dialog.add_title')
      "
      :action-disabled="!valid"
      @confirm="managePrice(formData, editMode)"
      @cancel="hideForm()"
    >
      <historic-price-form
        v-model="formData"
        :edit="editMode"
        @valid="valid = $event"
      />
    </big-dialog>
  </v-container>
</template>

<script setup lang="ts">
import BigDialog from '@/components/dialogs/BigDialog.vue';
import HistoricPriceForm from '@/components/price-manager/historic/HistoricPriceForm.vue';
import HistoricPriceTable from '@/components/price-manager/historic/HistoricPriceTable.vue';
import { useRoute, useRouter } from '@/composables/router';
import {
  HistoricalPrice,
  HistoricalPriceFormPayload
} from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useMessageStore } from '@/store/message';
import { Nullable } from '@/types';

const emptyPrice: () => HistoricalPriceFormPayload = () => ({
  fromAsset: '',
  toAsset: '',
  price: '0',
  timestamp: 0
});

const refreshing = ref(false);
const formData = ref<HistoricalPriceFormPayload>(emptyPrice());
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

const { setMessage } = useMessageStore();
const router = useRouter();
const route = useRoute();
const { tc } = useI18n();

const openForm = (hPrice: HistoricalPrice | null = null) => {
  set(editMode, !!hPrice);
  if (hPrice) {
    set(formData, {
      ...hPrice,
      price: hPrice.price.toFixed() ?? ''
    });
  } else {
    const emptyPriceObj = emptyPrice();
    set(formData, {
      ...emptyPriceObj,
      fromAsset: filter.fromAsset ?? '',
      toAsset: filter.toAsset ?? ''
    });
  }
  set(showForm, true);
};

const hideForm = function () {
  set(showForm, false);
  set(formData, emptyPrice());
};

const managePrice = async (
  price: HistoricalPriceFormPayload,
  edit: boolean
) => {
  try {
    if (edit) {
      await api.assets.editHistoricalPrice(price);
    } else {
      await api.assets.addHistoricalPrice(price);
    }

    set(showForm, false);
    if (!get(refreshing)) {
      set(refreshing, true);
    }
  } catch (e: any) {
    const values = { message: e.message };
    const title = edit
      ? tc('price_management.edit.error.title')
      : tc('price_management.add.error.title');
    const description = edit
      ? tc('price_management.edit.error.description', 0, values)
      : tc('price_management.add.error.description', 0, values);
    setMessage({
      title,
      description,
      success: false
    });
  }
};

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    openForm();
    await router.replace({ query: {} });
  }
});
</script>
