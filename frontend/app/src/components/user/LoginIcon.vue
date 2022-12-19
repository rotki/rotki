<script setup lang="ts">
defineProps({
  left: {
    required: false,
    type: Boolean,
    default: false
  }
});
const css = useCssModule();
</script>

<template>
  <div
    :class="{
      [css.icon]: true,
      [css['icon--right']]: !left,
      [css['icon--left']]: left
    }"
  >
    <slot />
  </div>
</template>

<style module lang="scss">
.icon {
  position: absolute !important;
  bottom: 12px;

  &--left {
    left: 12px;
  }

  &--right {
    right: 12px;
  }

  @media (max-width: 700px) {
    top: 12px;
    bottom: auto;
  }
}
</style>
