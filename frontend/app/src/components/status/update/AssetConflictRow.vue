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

const { field } = toRefs(props);

const isStarted = computed(() => get(field) === 'started');
const isAddress = computed(() => get(field) === 'address');
</script>

<template>
  <div class="my-2 flex">
    <div class="font-medium">{{ field }}:</div>
    <div class="ml-4" :class="diff ? 'font-bold text-rui-error' : null">
      <span v-if="isStarted">
        <DateDisplay v-if="value" :timestamp="value" />
        <span v-else>-</span>
      </span>
      <span v-else-if="isAddress">
        <HashLink v-if="value" :text="value" no-link />
        <span v-else>-</span>
      </span>
      <span v-else>
        {{ value }}
      </span>
    </div>
  </div>
</template>
