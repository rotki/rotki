<script setup lang="ts">
import About from '@/components/About.vue';
import AppCore from '@/components/app/AppCore.vue';
import AppHost from '@/components/app/AppHost.vue';
import AppMessages from '@/components/app/AppMessages.vue';
import AppUpdatePopup from '@/components/status/update/AppUpdatePopup.vue';
import { useDataLoader } from '@/composables/session/load';
import { useAreaVisibilityStore } from '@/store/session/visibility';

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
