<script setup lang="ts">
const { showAbout } = storeToRefs(useAreaVisibilityStore());
const { isPackaged } = useInterop();
const { updateDarkMode } = useDarkMode();
updateDarkMode(false);

const css = useCssModule();
</script>

<template>
  <AppHost>
    <FrontendUpdateNotifier v-if="!isPackaged" />
    <AppMessages>
      <div :class="css.overlay">
        <div :class="css.overlay__scroll">
          <RouterView />
        </div>
      </div>
    </AppMessages>
    <VDialog v-if="showAbout" v-model="showAbout" max-width="500">
      <About />
    </VDialog>
  </AppHost>
</template>

<style lang="scss" module>
.overlay {
  &__scroll {
    @apply flex flex-col-reverse lg:flex-row w-full lg:h-screen min-h-screen;
  }

  @apply block overflow-auto lg:overflow-hidden w-full lg:h-screen min-h-screen fixed top-0 bottom-0;
}
</style>
