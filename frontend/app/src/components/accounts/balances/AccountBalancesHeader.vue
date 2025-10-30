<script setup lang="ts">
import { toSentenceCase } from '@rotki/common';

interface Props {
  category: string;
  isEvm: boolean;
}

defineProps<Props>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <template v-if="$slots.default">
    <slot />
  </template>
  <template v-else>
    {{ t('account_balances.data_table.group', { type: isEvm ? 'EVM' : toSentenceCase(category) }) }}
  </template>
</template>
