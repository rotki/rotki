<script setup lang="ts">
defineProps<{ expanded: boolean }>();

const emit = defineEmits(['click']);
const click = () => emit('click');
</script>

<template>
  <span>
    <RuiButton icon variant="text" @click="click()">
      <VIcon :class="{ icon: true, 'icon--expanded': expanded }">
        mdi-chevron-down
      </VIcon>
    </RuiButton>
  </span>
</template>

<style scoped lang="scss">
.icon {
  &--expanded {
    transition: 0.2s all 0s;
    transform: rotate(-180deg);
  }
}
</style>
