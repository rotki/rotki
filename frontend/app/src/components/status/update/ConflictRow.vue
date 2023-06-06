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
  <v-row class="mt-2 mb-2" no-gutters>
    <v-col cols="auto" class="font-weight-medium"> {{ field }}: </v-col>
    <v-col class="ms-4" :class="diff ? 'red--text font-weight-bold' : null">
      <span v-if="isStarted">
        <date-display v-if="value" :timestamp="value" />
        <span v-else>-</span>
      </span>
      <span v-else-if="isAddress">
        <hash-link v-if="value" :text="value" no-link />
        <span v-else>-</span>
      </span>
      <span v-else>
        {{ value }}
      </span>
    </v-col>
  </v-row>
</template>
