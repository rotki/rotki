<script setup lang="ts">
import {
  NotificationCategory,
  type NotificationPayload,
  Severity
} from '@rotki/common/lib/messages';
import { type Nullable } from '@/types';
import {
  type HistoricalPrice,
  type HistoricalPriceFormPayload,
  type ManualPricePayload
} from '@/types/prices';

const emptyPrice: () => HistoricalPriceFormPayload = () => ({
  fromAsset: '',
  toAsset: '',
  price: '0',
  timestamp: 0
});

const formData = ref<HistoricalPriceFormPayload>(emptyPrice());
const filter = reactive<{
  fromAsset: Nullable<string>;
  toAsset: Nullable<string>;
}>({
  fromAsset: null,
  toAsset: null
});
const editMode = ref(false);

const { setMessage } = useMessageStore();
const {
  editHistoricalPrice,
  addHistoricalPrice,
  fetchHistoricalPrices,
  deleteHistoricalPrice
} = useAssetPricesApi();
const router = useRouter();
const route = useRoute();
const { t } = useI18n();

const {
  openDialog,
  setOpenDialog,
  submitting,
  closeDialog,
  setSubmitFunc,
  trySubmit,
  setPostSubmitFunc
} = useHistoricPriceForm();

const prices: Ref<HistoricalPrice[]> = ref([]);
const loading: Ref<boolean> = ref(false);
const { notify } = useNotificationsStore();

const fetchPrices = async (payload?: Partial<ManualPricePayload>) => {
  set(loading, true);
  try {
    set(prices, await fetchHistoricalPrices(payload));
  } catch (e: any) {
    const notification: NotificationPayload = {
      title: t('price_table.fetch.failure.title'),
      message: t('price_table.fetch.failure.message', {
        message: e.message
      }),
      display: true,
      severity: Severity.ERROR,
      category: NotificationCategory.DEFAULT
    };
    notify(notification);
  } finally {
    set(loading, false);
  }
};

const { resetHistoricalPricesData } = useHistoricCachePriceStore();

const refresh = async (payload?: {
  modified?: boolean;
  additionalEntry?: HistoricalPrice;
}) => {
  await fetchPrices(get(filter));

  if (payload?.modified) {
    const items: HistoricalPrice[] = [...get(prices)];
    if (payload?.additionalEntry) {
      items.push(payload.additionalEntry);
    }
    resetHistoricalPricesData(items);
  }
};

watch(
  filter,
  async () => {
    await refresh();
  },
  { deep: true }
);

onBeforeMount(refresh);

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
  setOpenDialog(true);
};

const hideForm = function () {
  closeDialog();
  set(formData, emptyPrice());
};

const save = async () => {
  const form = get(formData);
  const isEdit = get(editMode);

  try {
    if (isEdit) {
      return await editHistoricalPrice(form);
    }
    return await addHistoricalPrice(form);
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

const { show } = useConfirmStore();

const showDeleteConfirmation = (item: HistoricalPrice) => {
  show(
    {
      title: t('price_table.delete.dialog.title'),
      message: t('price_table.delete.dialog.message')
    },
    () => deletePrice(item)
  );
};

const deletePrice = async (item: HistoricalPrice) => {
  const { price, ...payload } = item!;
  try {
    await deleteHistoricalPrice(payload);
    await refresh({
      modified: true,
      additionalEntry: item
    });
  } catch (e: any) {
    const notification: NotificationPayload = {
      title: t('price_table.delete.failure.title'),
      message: t('price_table.delete.failure.message', {
        message: e.message
      }),
      display: true,
      severity: Severity.ERROR,
      category: NotificationCategory.DEFAULT
    };
    notify(notification);
  }
};

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    openForm();
    await router.replace({ query: {} });
  }
});

setPostSubmitFunc(() => refresh({ modified: true }));
</script>

<template>
  <v-container>
    <v-row justify="space-between" align="center" no-gutters>
      <v-col>
        <card-title>{{ t('price_management.historic.title') }}</card-title>
      </v-col>
    </v-row>
    <card class="mt-8">
      <template #title>{{ t('price_management.filter_title') }}</template>
      <v-row>
        <v-col cols="12" md="6">
          <asset-select
            v-model="filter.fromAsset"
            outlined
            :label="t('price_management.from_asset')"
            clearable
            hide-details
          />
        </v-col>
        <v-col cols="12" md="6">
          <asset-select
            v-model="filter.toAsset"
            outlined
            :label="t('price_management.to_asset')"
            clearable
            hide-details
          />
        </v-col>
      </v-row>
    </card>
    <historic-price-table
      class="mt-12"
      :items="prices"
      :loading="loading"
      @refresh="refresh($event)"
      @edit="openForm($event)"
      @delete="showDeleteConfirmation($event)"
    >
      <v-btn absolute fab top right color="primary" @click="openForm()">
        <v-icon> mdi-plus </v-icon>
      </v-btn>
    </historic-price-table>
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
      <historic-price-form v-model="formData" :edit="editMode" />
    </big-dialog>
  </v-container>
</template>
