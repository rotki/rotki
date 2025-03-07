<script setup lang="ts">
import About from '@/components/About.vue';
import AppCore from '@/components/app/AppCore.vue';
import AppHost from '@/components/app/AppHost.vue';
import AppMessages from '@/components/app/AppMessages.vue';
import FrontendUpdateNotifier from '@/components/status/FrontendUpdateNotifier.vue';
import AppUpdatePopup from '@/components/status/update/AppUpdatePopup.vue';
import { useDarkMode } from '@/composables/dark-mode';
import { useInterop } from '@/composables/electron-interop';
import { usePremium } from '@/composables/premium';
import { useDataLoader } from '@/composables/session/load';
import { ThemeChecker } from '@/premium/premium';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const { showAbout } = storeToRefs(useAreaVisibilityStore());
const premium = usePremium();
const { isPackaged } = useInterop();
const { updateDarkMode } = useDarkMode();
const { load } = useDataLoader();

onMounted(load);
</script>

<template>
  <AppHost>
    <AppMessages>
      <ThemeChecker
        v-if="premium"
        @update:dark-mode="updateDarkMode($event)"
      />
      <AppUpdatePopup />
      <AppCore />
    </AppMessages>
    <RuiDialog
      v-model="showAbout"
      max-width="500"
    >
      <About />
    </RuiDialog>
    <FrontendUpdateNotifier v-if="!isPackaged" />
  </AppHost>
</template>
