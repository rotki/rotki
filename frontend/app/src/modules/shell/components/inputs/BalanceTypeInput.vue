<script setup lang="ts">
import type { RuiMenuSelect } from '@rotki/ui-library';

import type { ForwardedProps } from '@/modules/core/common/forwarded-props';
import { BalanceType } from '@/modules/balances/types/balances';

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<BalanceType>({ required: true });

defineProps<
  /* @vue-ignore */ ForwardedProps<typeof RuiMenuSelect>
>();

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
    key-attr="key"
    text-attr="label"
  />
</template>
