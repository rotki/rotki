<template>
  <v-tooltip top open-delay="400">
    <template #activator="{ on, attrs }">
      <v-btn small v-bind="attrs" icon @click="copy()" v-on="on">
        <v-icon small>mdi-content-copy</v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>

<script setup lang="ts">
const props = defineProps({
  value: { required: true, type: String },
  tooltip: { required: true, type: String }
});

const { value } = toRefs(props);
const { copy } = useClipboard({ source: value });
</script>
