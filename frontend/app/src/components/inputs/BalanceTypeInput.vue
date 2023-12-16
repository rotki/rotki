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

const { t } = useI18n();

const model = useSimpleVModel(props, emit);

const balanceTypes = computed(() => [
  {
    key: BalanceType.ASSET,
    label: t('common.asset'),
  },
  {
    key: BalanceType.LIABILITY,
    label: t('manual_balances_form.type.liability'),
  },
]);
</script>

<template>
  <RuiMenuSelect
    v-model="model"
    :options="balanceTypes"
    v-bind="$attrs"
    variant="outlined"
    key-attr="key"
    text-attr="label"
  />
</template>
