<script setup lang="ts">
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import AppHost from '@/modules/shell/app/AppHost.vue';
import AppMessages from '@/modules/shell/app/AppMessages.vue';
import AppUpdatePopup from '@/modules/shell/app/AppUpdatePopup.vue';
import About from '@/modules/shell/components/About.vue';

const { showAbout } = storeToRefs(useAreaVisibilityStore());
</script>

<template>
  <AppHost>
    <AppMessages>
      <AppUpdatePopup />
      <div class="block overflow-auto lg:overflow-hidden w-full lg:h-screen min-h-screen fixed top-0 bottom-0 dark:bg-dark-elevated">
        <div class="flex flex-col-reverse lg:flex-row w-full lg:h-screen min-h-screen">
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
