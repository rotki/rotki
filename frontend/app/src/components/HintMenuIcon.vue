<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

const attrs = useAttrs();
</script>

<template>
  <RuiMenu
    menu-class="max-w-[25rem]"
    v-bind="attrs"
  >
    <template #activator="{ on }">
      <RuiButton
        variant="text"
        icon
        v-on="on"
      >
        <RuiIcon name="question-line" />
      </RuiButton>
    </template>
    <div
      class="p-4 py-3"
    >
      <slot />
    </div>
  </RuiMenu>
</template>
