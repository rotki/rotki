<script setup lang="ts">
import BankConnectorIcon from '@/modules/banks/components/BankConnectorIcon.vue';

/** A bank as one line: its connector's icon and its connector or institute name. */
const { connector, name } = defineProps<{
  connector: string;
  name: string;
}>();
</script>

<template>
  <span
    class="flex items-center gap-2 min-w-0"
    :title="connector"
  >
    <BankConnectorIcon :connector="connector" />
    <span class="truncate">{{ name }}</span>
  </span>
</template>
