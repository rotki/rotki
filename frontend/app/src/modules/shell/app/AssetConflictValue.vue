<script setup lang="ts">
import type { UnderlyingToken } from '@rotki/common';
import { computed } from 'vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { field, value } = defineProps<{
  field: string;
  value?: string | number | boolean | null | UnderlyingToken[];
}>();

const started = computed<number | undefined>(() => (field === 'started' && typeof value === 'number' ? value : undefined));
const address = computed<string | undefined>(() => (field === 'address' && typeof value === 'string' ? value : undefined));
/** A date or address field without a usable value reads as a dash, like a missing one. */
const empty = computed<boolean>(() => {
  if (field === 'started' || field === 'address')
    return true;
  return value === undefined || value === null || value === '';
});
</script>

<template>
  <DateDisplay
    v-if="started"
    :timestamp="started"
  />
  <HashLink
    v-else-if="address"
    :text="address"
    display-mode="copy"
  />
  <span v-else-if="empty">-</span>
  <span
    v-else
    class="break-all"
  >
    {{ value }}
  </span>
</template>
