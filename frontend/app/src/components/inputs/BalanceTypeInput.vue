<script setup lang="ts">
import { BalanceType } from '@/types/balances';

defineProps<{ value: BalanceType }>();

const emit = defineEmits<{ (e: 'input', value: BalanceType): void }>();

const { t } = useI18n();
const balanceTypes = computed(() => [
  {
    value: BalanceType.ASSET,
    text: t('common.asset')
  },
  {
    value: BalanceType.LIABILITY,
    text: t('manual_balances_form.type.liability')
  }
]);

const input = (value: BalanceType) => {
  emit('input', value);
};
</script>

<template>
  <VSelect
    :value="value"
    :items="balanceTypes"
    v-bind="$attrs"
    @input="input($event)"
  />
</template>
