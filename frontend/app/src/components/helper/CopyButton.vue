<script setup lang="ts">
const props = defineProps({
  value: { required: true, type: String },
  tooltip: { required: true, type: String }
});

const { value } = toRefs(props);
const { copy } = useClipboard({ source: value });
</script>

<template>
  <VTooltip top open-delay="400">
    <template #activator="{ on, attrs }">
      <VBtn small v-bind="attrs" icon @click="copy()" v-on="on">
        <VIcon small>mdi-content-copy</VIcon>
      </VBtn>
    </template>
    <span>{{ tooltip }}</span>
  </VTooltip>
</template>
