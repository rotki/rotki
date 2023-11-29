<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { type ManualPriceFormPayload } from '@/types/prices';
import { toMessages } from '@/utils/validation';

const props = defineProps<{
  value: ManualPriceFormPayload;
  edit: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', price: Partial<ManualPriceFormPayload>): void;
}>();

const { value } = toRefs(props);
const { assetSymbol } = useAssetInfoRetrieval();

const fromAsset = computed(({ value }) => get(assetSymbol(value.fromAsset)));
const toAsset = computed(({ value }) => get(assetSymbol(value.toAsset)));

const price = ref<string>('');
const numericPrice = bigNumberifyFromRef(price);

const input = (price: Partial<ManualPriceFormPayload>) => {
  emit('input', { ...get(value), ...price });
};

watch(value, val => {
  set(price, val.price);
});

watch(price, val => {
  input({ price: val });
});

onMounted(() => {
  set(price, get(value).price);
});

const { t } = useI18n();

const rules = {
  fromAsset: {
    required: helpers.withMessage(
      t('price_form.from_non_empty').toString(),
      required
    )
  },
  toAsset: {
    required: helpers.withMessage(
      t('price_form.to_non_empty').toString(),
      required
    )
  },
  price: {
    required: helpers.withMessage(
      t('price_form.price_non_empty').toString(),
      required
    )
  }
};

const { setValidation } = useLatestPriceForm();

const v$ = setValidation(
  rules,
  {
    fromAsset: computed(() => get(value).fromAsset),
    toAsset: computed(() => get(value).toAsset),
    price: computed(() => get(value).price)
  },
  { $autoDirty: true }
);
</script>

<template>
  <form class="flex flex-col gap-2">
    <div class="grid md:grid-cols-2 gap-x-4">
      <AssetSelect
        :value="value.fromAsset"
        :label="t('price_form.from_asset')"
        outlined
        include-nfts
        :disabled="edit"
        :error-messages="toMessages(v$.fromAsset)"
        @input="input({ fromAsset: $event })"
      />
      <AssetSelect
        :value="value.toAsset"
        :label="t('price_form.to_asset')"
        outlined
        :error-messages="toMessages(v$.toAsset)"
        @input="input({ toAsset: $event })"
      />
    </div>
    <AmountInput
      v-model="price"
      outlined
      :error-messages="toMessages(v$.price)"
      :label="t('common.price')"
    />
    <i18n
      v-if="price && fromAsset && toAsset"
      tag="div"
      path="price_form.latest.hint"
      class="text-caption text-rui-success -mt-8 pb-1 pl-3"
    >
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
          <AmountDisplay :value="numericPrice" :tooltip="false" />
        </strong>
      </template>
    </i18n>
  </form>
</template>
