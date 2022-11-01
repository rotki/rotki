<template>
  <v-container>
    <v-row justify="space-between" align="center" no-gutters>
      <v-col>
        <card-title>{{ tc('price_management.latest.title') }}</card-title>
      </v-col>
    </v-row>
    <card class="mt-8">
      <template #title>{{ tc('price_management.filter_title') }}</template>
      <v-row>
        <v-col>
          <asset-select
            v-model="assetFilter"
            outlined
            :label="tc('price_management.from_asset')"
            clearable
            hide-details
          />
        </v-col>
      </v-row>
    </card>
    <latest-price-table
      class="mt-12"
      :asset-filter="assetFilter"
      :refreshing="refreshing"
      @edit="openForm($event)"
      @refreshed="refreshing = false"
    >
      <v-btn absolute fab top right color="primary" @click="openForm()">
        <v-icon> mdi-plus </v-icon>
      </v-btn>
    </latest-price-table>
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
      <latest-price-form
        v-model="formData"
        :edit="editMode"
        @valid="valid = $event"
      />
    </big-dialog>
  </v-container>
</template>
<script setup lang="ts">
import { omit } from 'lodash';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import LatestPriceForm from '@/components/price-manager/latest/LatestPriceForm.vue';
import LatestPriceTable from '@/components/price-manager/latest/LatestPriceTable.vue';
import { ManualPrice, ManualPriceFormPayload } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useMessageStore } from '@/store/message';
import { Nullable } from '@/types';

const emptyPrice: () => ManualPriceFormPayload = () => ({
  fromAsset: '',
  toAsset: '',
  price: '0'
});

const refreshing = ref(false);
const formData = ref<ManualPriceFormPayload>(emptyPrice());
const showForm = ref(false);

const assetFilter = ref<Nullable<string>>(null);
const valid = ref(false);
const editMode = ref(false);

const { setMessage } = useMessageStore();
const router = useRouter();
const route = useRoute();
const { tc } = useI18n();

const openForm = (cPrice: ManualPrice | null = null) => {
  set(editMode, !!cPrice);
  if (cPrice) {
    set(formData, {
      ...cPrice,
      price: cPrice.price.toFixed() ?? ''
    });
  } else {
    const emptyPriceObj = emptyPrice();
    set(formData, {
      ...emptyPriceObj,
      fromAsset: get(assetFilter) ?? ''
    });
  }
  set(showForm, true);
};

const hideForm = function () {
  set(showForm, false);
  set(formData, emptyPrice());
};

const managePrice = async (price: ManualPriceFormPayload, edit: boolean) => {
  try {
    await api.assets.addLatestPrice(omit(price, 'usdPrice'));
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
