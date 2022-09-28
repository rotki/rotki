<template>
  <span>
    <v-btn icon @click="click">
      <v-icon :class="{ icon: true, 'icon--expanded': expanded }">
        mdi-chevron-down
      </v-icon>
    </v-btn>
  </span>
</template>

<script setup lang="ts">
defineProps({
  expanded: { required: true, type: Boolean }
});

const emit = defineEmits(['click']);
const click = () => emit('click');
</script>

<style scoped lang="scss">
.icon {
  &--expanded {
    transition: 0.2s all 0s;
    transform: rotate(-180deg);
  }
}
</style>
