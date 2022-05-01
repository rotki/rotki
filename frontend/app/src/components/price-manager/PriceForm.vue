<template>
  <v-form v-model="valid">
    <v-row class="mt-2">
      <v-col cols="12" md="6">
        <asset-select
          :value="value.fromAsset"
          :label="$t('price_form.from_asset')"
          outlined
          :disabled="edit"
          :rules="fromAssetRules"
          @input="input({ fromAsset: $event })"
        />
      </v-col>
      <v-col cols="12" md="6">
        <asset-select
          :value="value.toAsset"
          :label="$t('price_form.to_asset')"
          :disabled="edit"
          outlined
          :rules="toAssetRules"
          @input="input({ toAsset: $event })"
        />
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <amount-input
          v-model="price"
          outlined
          :rules="priceRules"
          :label="$t('price_form.price')"
        />
        <div v-if="price" class="text-caption green--text mt-n6 pb-1 pl-3">
          <i18n tag="div" path="price_form.hint">
            <template #fromAsset>
              <strong>
                {{ fromAsset }}
              </strong>
            </template>
            <template #toAsset>
              <strong>
                {{ toAsset }}
              </strong>
            </template>
            <template #price>
              <strong>
                <amount-display :value="numericPrice" :tooltip="false" />
              </strong>
            </template>
          </i18n>
        </div>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <date-time-picker
          :value="date"
          outlined
          :label="$t('price_form.date')"
          seconds
          :disabled="edit"
          :rules="dateRules"
          @input="input({ timestamp: convertToTimestamp($event) })"
        />
      </v-col>
    </v-row>
  </v-form>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import AssetMixin from '@/mixins/asset-mixin';
import { HistoricalPriceFormPayload } from '@/services/assets/types';
import { useAssetInfoRetrieval } from '@/store/assets';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

export default defineComponent({
  name: 'PriceForm',
  mixins: [AssetMixin],
  props: {
    value: {
      required: true,
      type: Object as PropType<HistoricalPriceFormPayload>
    },
    edit: {
      required: true,
      type: Boolean
    }
  },
  emits: ['input', 'valid'],
  setup(props, { emit }) {
    const { value } = toRefs(props);
    const { assetSymbol } = useAssetInfoRetrieval();

    const valid = ref(false);

    const date = computed(({ value }) =>
      value.timestamp ? convertFromTimestamp(value.timestamp, true) : ''
    );
    const fromAsset = computed(({ value }) =>
      get(assetSymbol(value.fromAsset))
    );
    const toAsset = computed(({ value }) => get(assetSymbol(value.toAsset)));

    const price = ref<string>('');
    const numericPrice = bigNumberifyFromRef(price);

    const input = (price: Partial<HistoricalPriceFormPayload>) => {
      emit('input', { ...get(value), ...price });
    };
    watch(valid, value => emit('valid', value));
    watch(value, val => {
      set(price, val.price);
    });

    watch(price, val => {
      input({ price: val });
    });

    onMounted(() => {
      set(price, get(value).price);
    });

    return {
      date,
      price,
      numericPrice,
      fromAsset,
      toAsset,
      valid,
      input,
      convertToTimestamp
    };
  },
  data() {
    return {
      fromAssetRules: [
        (v: string) => !!v || this.$t('price_form.from_non_empty').toString()
      ],
      toAssetRules: [
        (v: string) => !!v || this.$t('price_form.to_non_empty').toString()
      ],
      priceRules: [
        (v: string) => !!v || this.$t('price_form.price_non_empty').toString()
      ],
      dateRules: [
        (v: string) => !!v || this.$t('price_form.date_non_empty').toString()
      ]
    };
  }
});
</script>
