<template>
  <v-select
    :value="value"
    :items="balanceTypes"
    v-bind="$attrs"
    @input="input"
  />
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { BalanceType } from '@/services/balances/types';

defineProps({
  value: {
    required: true,
    type: String as PropType<BalanceType>
  }
});

const emit = defineEmits(['input']);

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
