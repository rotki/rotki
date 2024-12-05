<script setup lang="ts">
import { ThemeChecker } from '@/premium/premium';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { useDataLoader } from '@/composables/session/load';
import { useDarkMode } from '@/composables/dark-mode';
import { useInterop } from '@/composables/electron-interop';
import { usePremium } from '@/composables/premium';

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
