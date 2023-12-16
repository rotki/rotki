<script setup lang="ts">
import { BalanceType } from '@/types/balances';

defineOptions({
  inheritAttrs: false,
});

const props = defineProps<{
  modelValue: BalanceType;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: BalanceType): void;
}>();

const model = useSimpleVModel(props, emit);

const { t } = useI18n();
const balanceTypes = computed(() => [
  {
    value: BalanceType.ASSET,
    text: t('common.asset'),
  },
  {
    value: BalanceType.LIABILITY,
    text: t('manual_balances_form.type.liability'),
  },
]);
</script>

<template>
  <VSelect
    v-model="model"
    :items="balanceTypes"
    v-bind="$attrs"
    variant="outlined"
  />
</template>
