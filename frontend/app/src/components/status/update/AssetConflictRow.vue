<script setup lang="ts">
import type { UnderlyingToken } from '@rotki/common';
import DateDisplay from '@/components/display/DateDisplay.vue';
import HashLink from '@/components/helper/HashLink.vue';

const props = defineProps<{
  field: string;
  value?: string | number | boolean | null | UnderlyingToken[];
  diff: boolean;
}>();

const isStarted = computed(() => props.field === 'started');
const isAddress = computed(() => props.field === 'address');
const started = computed(() => {
  if (typeof props.value === 'number')
    return props.value;

  return undefined;
});
const address = computed(() => {
  if (typeof props.value === 'string')
    return props.value;

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
          no-link
        />
        <span v-else>-</span>
      </span>
      <span v-else>
        {{ value }}
      </span>
    </div>
  </div>
</template>
