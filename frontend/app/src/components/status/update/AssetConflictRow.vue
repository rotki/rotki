<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    field: string;
    value?: string | number | null;
    diff: boolean;
  }>(),
  {
    value: null
  }
);

const isStarted = computed(() => props.field === 'started');
const isAddress = computed(() => props.field === 'address');
const started = computed(() => {
  if (typeof props.value === 'number') {
    return props.value;
  }
  return undefined;
});
const address = computed(() => {
  if (typeof props.value === 'string') {
    return props.value;
  }
  return undefined;
});
</script>

<template>
  <div class="my-2 flex">
    <div class="font-medium">{{ field }}:</div>
    <div class="ml-4" :class="diff ? 'font-bold text-rui-error' : null">
      <span v-if="isStarted">
        <DateDisplay v-if="started" :timestamp="started" />
        <span v-else>-</span>
      </span>
      <span v-else-if="isAddress">
        <HashLink v-if="address" :text="address" no-link />
        <span v-else>-</span>
      </span>
      <span v-else>
        {{ value }}
      </span>
    </div>
  </div>
</template>
