<script setup lang="ts">
import { useDataLoader } from '@/modules/auth/use-session-load';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import AppCore from '@/modules/shell/app/AppCore.vue';
import AppHost from '@/modules/shell/app/AppHost.vue';
import AppMessages from '@/modules/shell/app/AppMessages.vue';
import AppUpdatePopup from '@/modules/shell/app/AppUpdatePopup.vue';
import About from '@/modules/shell/components/About.vue';

const { showAbout } = storeToRefs(useAreaVisibilityStore());
const { load } = useDataLoader();

onMounted(load);
</script>

<template>
  <AppHost>
    <AppMessages>
      <AppUpdatePopup />
      <AppCore />
    </AppMessages>
    <RuiDialog
      v-model="showAbout"
      max-width="500"
    >
      <About />
    </RuiDialog>
  </AppHost>
</template>
