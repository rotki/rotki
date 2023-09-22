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
      <RuiButton
        size="sm"
        v-bind="attrs"
        icon
        variant="text"
        @click="copy()"
        v-on="on"
      >
        <VIcon small>mdi-content-copy</VIcon>
      </RuiButton>
    </template>
    <span>{{ tooltip }}</span>
  </VTooltip>
</template>
