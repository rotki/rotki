<script setup lang="ts">
/**
 * @deprecated
 * Used to make some vuetify components that teleported by ui-library works. (For Tooltip, Menu, Dialog, and BottomSheet contents)
 * Remove this if there's no vuetify components inside the content anymore
 */
</script>

<template>
  <VApp class="!bg-transparent">
    <slot />
  </VApp>
</template>
