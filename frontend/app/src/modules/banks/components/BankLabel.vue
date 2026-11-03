<script setup lang="ts">
import BankConnectorIcon from '@/modules/banks/components/BankConnectorIcon.vue';

/** A bank as one line: its logo and its connector or institute name. */
const { bankCode, connector, name } = defineProps<{
  connector: string;
  name: string;
  bankCode?: string | null;
}>();
</script>

<template>
  <span class="flex items-center gap-2 min-w-0">
    <BankConnectorIcon
      :connector="connector"
      :bank-code="bankCode"
    />
    <span class="truncate">{{ name }}</span>
  </span>
</template>
