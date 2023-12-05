<script setup lang="ts">
import { type NonFungibleBalance } from '@/types/nfbalances';

const props = defineProps<{ value: NonFungibleBalance }>();

const emit = defineEmits(['close', 'save']);

const { value } = toRefs(props);
const asset = ref<string | null>(null);
const price = ref<string | null>(null);
const valid = computed(
  () => get(asset) && get(price) && !isNaN(Number.parseInt(get(price)!))
);
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

<template>
  <VDialog
    :value="true"
    max-width="550px"
    @close="close()"
    @click:outside="close()"
  >
    <RuiCard>
      <template #header>{{ t('non_fungible_balances.edit.title') }}</template>
      <template #subheader> {{ value.name }}</template>
      <AssetSelect v-model="asset" outlined />
      <AmountInput
        v-model="price"
        :label="t('common.price')"
        outlined
        single-line
        @keypress.enter="save()"
      />
      <template #footer>
        <div class="grow" />
        <RuiButton variant="text" color="primary" @click="close()">
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton color="primary" :disabled="!valid" @click="save()">
          {{ t('common.actions.save') }}
        </RuiButton>
      </template>
    </RuiCard>
  </VDialog>
</template>
