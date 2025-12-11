<script setup lang="ts">
import About from '@/components/About.vue';
import AppHost from '@/components/app/AppHost.vue';
import AppMessages from '@/components/app/AppMessages.vue';
import AppUpdatePopup from '@/components/status/update/AppUpdatePopup.vue';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const { showAbout } = storeToRefs(useAreaVisibilityStore());
</script>

<template>
  <AppHost>
    <AppMessages>
      <AppUpdatePopup />
      <div class="block overflow-auto lg:overflow-hidden w-full lg:h-screen min-h-screen fixed top-0 bottom-0 dark:bg-[#1E1E1E]">
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
