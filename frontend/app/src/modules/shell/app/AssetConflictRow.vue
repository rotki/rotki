<script setup lang="ts">
import type { UnderlyingToken } from '@rotki/common';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { field, value } = defineProps<{
  field: string;
  value?: string | number | boolean | null | UnderlyingToken[];
  diff: boolean;
}>();

const isStarted = computed(() => field === 'started');
const isAddress = computed(() => field === 'address');
const started = computed(() => {
  if (typeof value === 'number')
    return value;

  return undefined;
});
const address = computed(() => {
  if (typeof value === 'string')
    return value;

  return undefined;
});
</script>

<template>
  <div class="my-2 flex">
    <div class="font-medium">
      {{ field }}:
    </div>
    <div
      class="ml-4"
      :class="diff ? 'font-bold text-rui-error' : null"
    >
      <span v-if="isStarted">
        <DateDisplay
          v-if="started"
          :timestamp="started"
        />
        <span v-else>-</span>
      </span>
      <span v-else-if="isAddress">
        <HashLink
          v-if="address"
          :text="address"
          display-mode="copy"
        />
        <span v-else>-</span>
      </span>
      <span v-else>
        {{ value }}
      </span>
    </div>
  </div>
</template>
