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
import { useHistoricCachePriceStore } from '@/store/prices/historic';

const emptyPrice: () => HistoricalPriceFormPayload = () => ({
  fromAsset: '',
  toAsset: '',
  price: '0',
  timestamp: 0
});

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
const { editHistoricalPrice, addHistoricalPrice, fetchHistoricalPrices } =
  useAssetPricesApi();
const router = useRouter();
const route = useRoute();
const { tc } = useI18n();

const prices: Ref<HistoricalPrice[]> = ref([]);
const loading: Ref<boolean> = ref(false);
const { notify } = useNotificationsStore();

const fetchPrices = async (payload?: Partial<ManualPricePayload>) => {
  set(loading, true);
  try {
    set(prices, await fetchHistoricalPrices(payload));
  } catch (e: any) {
    const notification: NotificationPayload = {
      title: tc('price_table.fetch.failure.title'),
      message: tc('price_table.fetch.failure.message', 0, {
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

const refresh = async (modified: boolean | HistoricalPrice = false) => {
  await fetchPrices(get(filter));

  if (modified) {
    const items: HistoricalPrice[] = [...get(prices)];
    if (typeof modified !== 'boolean') {
      items.push(modified);
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
      await editHistoricalPrice(price);
    } else {
      await addHistoricalPrice(price);
    }

    set(showForm, false);
    await refresh(true);
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
      :items="prices"
      :loading="loading"
      @refresh="refresh($event)"
      @edit="openForm($event)"
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
