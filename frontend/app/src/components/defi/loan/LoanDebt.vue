<script setup lang="ts">
import { type Balance } from '@rotki/common';
import { type PropType } from 'vue';

defineProps({
  debt: {
    required: true,
    type: Object as PropType<Balance>
  },
  asset: {
    required: false,
    type: String,
    default: ''
  }
});

const { t } = useI18n();
</script>

<template>
  <stat-card :title="t('loan_debt.title')" :class="$style.debt">
    <loan-row :title="t('loan_debt.outstanding_debt')">
      <balance-display :asset="asset" :value="debt" />
    </loan-row>
    <slot />
  </stat-card>
</template>

<style module lang="scss">
.debt {
  height: 100%;
}
</style>
