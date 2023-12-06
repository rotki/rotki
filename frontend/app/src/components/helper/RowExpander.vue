<script setup lang="ts">
defineProps<{ expanded: boolean }>();

const emit = defineEmits<{
  (e: 'click'): void;
}>();
const click = () => emit('click');
</script>

<template>
  <RuiButton variant="text" class="!p-2" icon @click="click()">
    <RuiIcon
      name="arrow-down-s-line"
      class="transition"
      size="20"
      :class="{ ['rotate-180']: expanded }"
    />
  </RuiButton>
</template>
