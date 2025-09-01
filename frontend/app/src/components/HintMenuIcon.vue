<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});
</script>

<template>
  <RuiMenu
    menu-class="max-w-[25rem]"
    v-bind="$attrs"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="text"
        icon
        v-bind="attrs"
      >
        <RuiIcon name="lu-circle-question-mark" />
      </RuiButton>
    </template>
    <div class="p-4 py-3">
      <slot />
    </div>
  </RuiMenu>
</template>
