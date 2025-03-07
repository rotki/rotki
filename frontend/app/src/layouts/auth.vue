<script setup lang="ts">
import About from '@/components/About.vue';
import AppHost from '@/components/app/AppHost.vue';
import AppMessages from '@/components/app/AppMessages.vue';
import FrontendUpdateNotifier from '@/components/status/FrontendUpdateNotifier.vue';
import { useDarkMode } from '@/composables/dark-mode';
import { useInterop } from '@/composables/electron-interop';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const { showAbout } = storeToRefs(useAreaVisibilityStore());
const { isPackaged } = useInterop();
const { updateDarkMode } = useDarkMode();
updateDarkMode(false);
</script>

<template>
  <AppHost>
    <FrontendUpdateNotifier v-if="!isPackaged" />
    <AppMessages>
      <div :class="$style.overlay">
        <div :class="$style.overlay__scroll">
          <RouterView />
        </div>
      </div>
    </AppMessages>
    <RuiDialog
      v-model="showAbout"
      max-width="500"
    >
      <About />
    </RuiDialog>
  </AppHost>
</template>

<style lang="scss" module>
.overlay {
  @apply block overflow-auto lg:overflow-hidden w-full lg:h-screen min-h-screen fixed top-0 bottom-0;

  &__scroll {
    @apply flex flex-col-reverse lg:flex-row w-full lg:h-screen min-h-screen;
  }
}
</style>
