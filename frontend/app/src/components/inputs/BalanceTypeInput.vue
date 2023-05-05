<script setup lang="ts">
import { type PropType } from 'vue';
import { BalanceType } from '@/types/balances';

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

<template>
  <v-select
    :value="value"
    :items="balanceTypes"
    v-bind="$attrs"
    @input="input($event)"
  />
</template>
