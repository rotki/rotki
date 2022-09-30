<template>
  <v-dialog
    :value="true"
    max-width="550px"
    @close="close"
    @click:outside="close"
  >
    <card>
      <template #title>{{ t('non_fungible_balance_edit.title') }}</template>
      <template #subtitle> {{ value.name }}</template>
      <asset-select v-model="asset" outlined />
      <amount-input
        v-model="price"
        :label="t('common.price')"
        outlined
        single-line
        @keypress.enter="save"
      />
      <template #buttons>
        <v-spacer />
        <v-btn depressed @click="close">
          {{ t('common.actions.cancel') }}
        </v-btn>
        <v-btn depressed color="primary" :disabled="!valid" @click="save">
          {{ t('common.actions.save') }}
        </v-btn>
      </template>
    </card>
  </v-dialog>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { NonFungibleBalance } from '@/types/nfbalances';
import { assert } from '@/utils/assertions';

const props = defineProps({
  value: {
    required: true,
    type: Object as PropType<NonFungibleBalance>
  }
});

const emit = defineEmits(['close', 'save']);

const { value } = toRefs(props);
const asset = ref<string | null>(null);
const price = ref<string | null>(null);
const valid = computed(() => {
  return get(asset) && get(price) && !isNaN(parseInt(get(price)!));
});
const close = () => emit('close');
const save = () => {
  assert(get(asset));
  assert(get(price));
  emit('save', { asset: get(asset), price: get(price) });
};
onMounted(() => {
  set(asset, get(value).priceAsset);
  set(price, get(value).priceInAsset.toFixed());
});

const { t } = useI18n();
</script>
