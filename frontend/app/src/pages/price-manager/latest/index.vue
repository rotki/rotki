<script setup lang="ts">
import omit from 'lodash/omit';
import { type Nullable } from '@/types';
import { type ManualPrice, type ManualPriceFormPayload } from '@/types/prices';

const emptyPrice: () => ManualPriceFormPayload = () => ({
  fromAsset: '',
  toAsset: '',
  price: '0'
});

const formData = ref<ManualPriceFormPayload>(emptyPrice());

const assetFilter = ref<Nullable<string>>(null);
const editMode = ref(false);

const { setMessage } = useMessageStore();
const router = useRouter();
const route = useRoute();
const { t } = useI18n();

const {
  openDialog,
  setOpenDialog,
  submitting,
  closeDialog,
  setSubmitFunc,
  trySubmit
} = useLatestPriceForm();

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
  setOpenDialog(true);
};

const hideForm = function () {
  closeDialog();
  set(formData, emptyPrice());
};

const { addLatestPrice } = useAssetPricesApi();

const save = async (): Promise<boolean> => {
  const form = get(formData);
  const isEdit = get(editMode);

  try {
    return await addLatestPrice(omit(form, 'usdPrice'));
  } catch (e: any) {
    const values = { message: e.message };
    const title = isEdit
      ? t('price_management.edit.error.title')
      : t('price_management.add.error.title');
    const description = isEdit
      ? t('price_management.edit.error.description', values)
      : t('price_management.add.error.description', values);

    setMessage({
      title,
      description,
      success: false
    });
    return false;
  }
};

setSubmitFunc(save);

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    openForm();
    await router.replace({ query: {} });
  }
});
</script>

<template>
  <v-container>
    <v-row justify="space-between" align="center" no-gutters>
      <v-col>
        <card-title>{{ t('price_management.latest.title') }}</card-title>
      </v-col>
    </v-row>
    <card class="mt-8">
      <template #title>{{ t('price_management.filter_title') }}</template>
      <v-row>
        <v-col>
          <asset-select
            v-model="assetFilter"
            outlined
            include-nfts
            :label="t('price_management.from_asset')"
            clearable
            hide-details
          />
        </v-col>
      </v-row>
    </card>
    <latest-price-table
      class="mt-12"
      :asset-filter="assetFilter"
      @edit="openForm($event)"
    >
      <v-btn absolute fab top right color="primary" @click="openForm()">
        <v-icon> mdi-plus </v-icon>
      </v-btn>
    </latest-price-table>
    <big-dialog
      :display="openDialog"
      :title="
        editMode
          ? t('price_management.dialog.edit_title')
          : t('price_management.dialog.add_title')
      "
      :loading="submitting"
      @confirm="trySubmit()"
      @cancel="hideForm()"
    >
      <latest-price-form v-model="formData" :edit="editMode" />
    </big-dialog>
  </v-container>
</template>
