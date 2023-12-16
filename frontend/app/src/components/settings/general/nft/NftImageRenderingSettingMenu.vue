<script setup lang="ts">
const dialogOpen = ref(false);
</script>

<template>
  <RuiMenu
    menu-class="max-w-[32rem] !z-[1]"
    :popper="{ placement: 'bottom-end' }"
    :persistent="dialogOpen"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="text"
        icon
        class="!p-2"
        v-bind="attrs"
      >
        <RuiIcon name="file-settings-line" />
      </RuiButton>
    </template>
    <NftImageRenderingSetting @dialog-open="dialogOpen = $event" />
  </RuiMenu>
</template>
