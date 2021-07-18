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
        <v-text-field
          :value="value.price"
          :rules="priceRules"
          :label="$t('price_form.price')"
          type="numeric"
          outlined
          :hint="
            $t('price_form.hint', {
              price,
              fromAsset,
              toAsset
            })
          "
          persistent-hint
          @input="price = $event"
        />
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
  inject,
  onMounted,
  PropType,
  ref,
  watch
} from '@vue/composition-api';
import { Store } from 'vuex';
import AssetMixin from '@/mixins/asset-mixin';
import { HistoricalPrice } from '@/services/assets/types';
import { AssetSymbolGetter } from '@/store/balances/types';
import { RotkehlchenState } from '@/store/types';
import { bigNumberify } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

export default defineComponent({
  name: 'PriceForm',
  mixins: [AssetMixin],
  props: {
    value: {
      required: true,
      type: Object as PropType<HistoricalPrice>
    },
    edit: {
      required: true,
      type: Boolean
    }
  },
  setup(props, { emit }) {
    const store = inject<Store<RotkehlchenState>>('vuex-store');
    const getSymbol = store!.getters[
      'balances/assetSymbol'
    ] as AssetSymbolGetter;
    const valid = ref(false);
    const date = computed(({ value }) =>
      value.timestamp ? convertFromTimestamp(value.timestamp, true) : ''
    );
    const fromAsset = computed(({ value }) => getSymbol(value.fromAsset));
    const toAsset = computed(({ value }) => getSymbol(value.toAsset));
    const price = ref('');
    const input = (price: Partial<HistoricalPrice>) => {
      emit('input', { ...props.value, ...price });
    };
    watch(valid, value => emit('valid', value));
    watch(props.value, value => {
      if (price.value.endsWith('.')) {
        return;
      }
      price.value = value.price.toString();
    });
    watch(price, value => {
      if (value.endsWith('.') || (value.includes('.') && value.endsWith('0'))) {
        return;
      }
      const bn = bigNumberify(value);
      if (bn.isFinite()) {
        input({ price: bn });
      }
    });

    onMounted(() => {
      price.value = props.value.price.toString();
    });

    return {
      date,
      price,
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
        (v: string) => !!v || this.$t('price_form.price_non_empty').toString(),
        (v: string) =>
          (!!v && bigNumberify(v).isFinite()) ||
          this.$t('price_form.price_nan').toString()
      ],
      dateRules: [
        (v: string) => !!v || this.$t('price_form.date_non_empty').toString()
      ]
    };
  }
});
</script>
