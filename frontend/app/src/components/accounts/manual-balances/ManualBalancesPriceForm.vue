<template>
  <div>
    <v-row>
      <v-col class="col" md="6">
        <amount-input
          :value="price"
          :disabled="fetchingPrice || !isCustomPrice || pending"
          :loading="fetchingPrice"
          outlined
          :label="tc('common.price')"
          @input="updatePrice"
        />
      </v-col>

      <v-col class="col" md="6">
        <asset-select
          :value="priceAsset"
          :disabled="fetchingPrice || !isCustomPrice || pending"
          :loading="fetchingPrice"
          outlined
          :label="tc('manual_balances_form.fields.price_asset')"
          @input="updatePriceAsset"
        />
      </v-col>
    </v-row>

    <v-row v-if="assetMethod === 0 && fetchedPrice" class="mt-n10 mb-0">
      <v-col cols="auto">
        <v-checkbox
          :value="isCustomPrice"
          :disabled="pending"
          :label="tc('manual_balances_form.fields.input_manual_price')"
          @change="updateCustomPrice"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { PropType } from 'vue';

defineProps({
  price: {
    required: true,
    type: String
  },
  priceAsset: {
    required: true,
    type: String
  },
  fetchedPrice: {
    required: true,
    type: String
  },
  fetchingPrice: {
    required: true,
    type: Boolean
  },
  isCustomPrice: {
    required: true,
    type: Boolean
  },
  pending: {
    required: true,
    type: Boolean
  },
  assetMethod: {
    required: false,
    type: Number as PropType<number | null>,
    default: 0
  }
});

const emit = defineEmits<{
  (e: 'update:price', price: string): void;
  (e: 'update:price-asset', priceAsset: string): void;
  (e: 'update:custom-price', customPrice: boolean): void;
}>();

const updatePrice = (price: string) => {
  emit('update:price', price);
};

const updatePriceAsset = (priceAsset: string) => {
  emit('update:price-asset', priceAsset);
};

const updateCustomPrice = (isCustomPrice: boolean) => {
  emit('update:custom-price', !!isCustomPrice);
};

const { tc } = useI18n();
</script>
