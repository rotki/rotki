<template>
  <v-dialog
    :value="true"
    max-width="550px"
    @close="close"
    @click:outside="close"
  >
    <card>
      <template #title>{{ $t('non_fungible_balance_edit.title') }}</template>
      <template #subtitle> {{ value.name }}</template>
      <asset-select v-model="asset" outlined />
      <amount-input
        v-model="price"
        :label="$t('non_fungible_balance_edit.price')"
        outlined
        single-line
        @keypress.enter="save"
      />
      <template #buttons>
        <v-spacer />
        <v-btn depressed @click="close">
          {{ $t('non_fungible_balance_edit.actions.cancel') }}
        </v-btn>
        <v-btn depressed color="primary" :disabled="!valid" @click="save">
          {{ $t('non_fungible_balance_edit.actions.save') }}
        </v-btn>
      </template>
    </card>
  </v-dialog>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import { NonFungibleBalance } from '@/store/balances/types';
import { assert } from '@/utils/assertions';

export default defineComponent({
  name: 'NonFungibleBalanceEdit',
  props: {
    value: {
      required: true,
      type: Object as PropType<NonFungibleBalance>
    }
  },
  emits: ['close', 'save'],
  setup(props, { emit }) {
    const { value } = toRefs(props);
    const asset = ref<string | null>(null);
    const price = ref<string | null>(null);
    const valid = computed(() => {
      return asset.value && price.value && !isNaN(parseInt(price.value));
    });
    const close = () => emit('close');
    const save = () => {
      assert(asset.value);
      assert(price.value);
      emit('save', { asset: asset.value, price: price.value });
    };
    onMounted(() => {
      asset.value = value.value.priceAsset;
      price.value = value.value.priceInAsset.toString();
    });
    return {
      valid,
      asset,
      price,
      close,
      save
    };
  }
});
</script>
