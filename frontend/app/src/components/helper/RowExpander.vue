<script setup lang="ts">
defineProps<{ expanded: boolean }>();

const emit = defineEmits(['click']);
const click = () => emit('click');
</script>

<template>
  <span>
    <VBtn icon @click="click()">
      <VIcon :class="{ icon: true, 'icon--expanded': expanded }">
        mdi-chevron-down
      </VIcon>
    </VBtn>
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
