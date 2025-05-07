<script setup lang="ts">
import { BalanceType } from '@/types/balances';

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<BalanceType>({ required: true });

const { t } = useI18n({ useScope: 'global' });

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
