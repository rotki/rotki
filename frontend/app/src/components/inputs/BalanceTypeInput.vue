<script setup lang="ts">
import { BalanceType } from '@/types/balances';
import { useSimpleVModel } from '@/utils/model';

const props = defineProps<{ value: BalanceType }>();

const emit = defineEmits<{ (e: 'input', value: BalanceType): void }>();

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
    full-width
    show-details
    key-attr="key"
    variant="outlined"
  />
</template>
