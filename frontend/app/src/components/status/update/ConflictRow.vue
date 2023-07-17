<script setup lang="ts">
const props = defineProps({
  field: { required: true, type: String },
  value: { required: false, type: [String, Number], default: null },
  diff: { required: true, type: Boolean }
});

const { field } = toRefs(props);

const isStarted = computed(() => get(field) === 'started');
const isAddress = computed(() => get(field) === 'address');
</script>

<template>
  <VRow class="mt-2 mb-2" no-gutters>
    <VCol cols="auto" class="font-weight-medium"> {{ field }}: </VCol>
    <VCol class="ms-4" :class="diff ? 'red--text font-weight-bold' : null">
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
    </VCol>
  </VRow>
</template>
