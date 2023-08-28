<script setup lang="ts">
const { showAbout } = storeToRefs(useAreaVisibilityStore());
const { isPackaged } = useInterop();
const { updateDarkMode } = useDarkMode();
updateDarkMode(false);
</script>

<template>
  <AppHost>
    <FrontendUpdateNotifier v-if="!isPackaged" />
    <AppMessages>
      <LoginHost />
    </AppMessages>
    <VDialog v-if="showAbout" v-model="showAbout" max-width="500">
      <About />
    </VDialog>
  </AppHost>
</template>
