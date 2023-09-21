<script setup lang="ts">
import { omit } from 'lodash-es';
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
  <VContainer>
    <VRow justify="space-between" align="center" no-gutters>
      <VCol>
        <CardTitle>{{ t('price_management.latest.title') }}</CardTitle>
      </VCol>
    </VRow>
    <Card class="mt-8">
      <template #title>{{ t('price_management.filter_title') }}</template>
      <VRow>
        <VCol>
          <AssetSelect
            v-model="assetFilter"
            outlined
            include-nfts
            :label="t('price_management.from_asset')"
            clearable
            hide-details
          />
        </VCol>
      </VRow>
    </Card>
    <LatestPriceTable
      class="mt-12"
      :asset-filter="assetFilter"
      @edit="openForm($event)"
    >
      <VBtn absolute fab top right color="primary" @click="openForm()">
        <VIcon> mdi-plus </VIcon>
      </VBtn>
    </LatestPriceTable>
    <BigDialog
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
      <LatestPriceForm v-model="formData" :edit="editMode" />
    </BigDialog>
  </VContainer>
</template>
