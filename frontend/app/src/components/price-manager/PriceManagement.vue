<template>
  <v-container>
    <v-row justify="space-between" align="center" no-gutters>
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
            :label="$tc('price_management.from_asset')"
            clearable
          />
        </v-col>
        <v-col cols="12" md="6">
          <asset-select
            v-model="filter.toAsset"
            outlined
            :label="$tc('price_management.to_asset')"
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
      @confirm="managePrice(priceForm, editMode)"
      @cancel="hideForm()"
    >
      <price-form
        v-model="priceForm"
        :edit="editMode"
        @valid="valid = $event"
      />
    </big-dialog>
  </v-container>
</template>

<script lang="ts">
import {
  defineComponent,
  onMounted,
  reactive,
  Ref,
  ref
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import PriceForm from '@/components/price-manager/PriceForm.vue';
import PriceTable from '@/components/price-manager/PriceTable.vue';
import { useRoute, useRouter } from '@/composables/common';
import i18n from '@/i18n';
import {
  HistoricalPrice,
  HistoricalPriceFormPayload
} from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/store';
import { Nullable } from '@/types';

const emptyPrice: () => HistoricalPriceFormPayload = () => ({
  fromAsset: '',
  toAsset: '',
  price: '0',
  timestamp: 0
});

const managePrice = (showForm: Ref<Boolean>, refresh: Ref<Boolean>) => {
  const { setMessage } = useMainStore();
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
      if (!get(refresh)) {
        set(refresh, true);
      }
    } catch (e: any) {
      const values = { message: e.message };
      const title = edit
        ? i18n.t('price_management.edit.error.title')
        : i18n.t('price_management.add.error.title');
      const description = edit
        ? i18n.t('price_management.edit.error.description', values)
        : i18n.t('price_management.add.error.description', values);
      setMessage({
        title: title.toString(),
        description: description.toString(),
        success: false
      });
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
    const refresh = ref(false);
    const priceForm = ref<HistoricalPriceFormPayload>(emptyPrice());
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

    const openForm = function (hPrice: HistoricalPrice | null = null) {
      set(editMode, !!hPrice);
      if (hPrice) {
        set(priceForm, {
          ...hPrice,
          price: hPrice.price.toFixed() ?? ''
        });
      } else {
        const emptyPriceObj = emptyPrice();
        set(priceForm, {
          ...emptyPriceObj,
          fromAsset: filter.fromAsset ?? '',
          toAsset: filter.toAsset ?? ''
        });
      }
      set(showForm, true);
    };

    const hideForm = function () {
      set(showForm, false);
      set(priceForm, emptyPrice());
    };

    const router = useRouter();
    const route = useRoute();

    onMounted(() => {
      const query = get(route).query;

      if (query.add) {
        openForm();
        router.replace({ query: {} });
      }
    });

    return {
      ...managePrice(showForm, refresh),
      refresh,
      filter,
      openForm,
      hideForm,
      showForm,
      editMode,
      priceForm,
      valid
    };
  }
});
</script>
