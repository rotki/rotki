<script setup lang="ts">
import { ThemeChecker } from '@/premium/premium';

const { showAbout } = storeToRefs(useAreaVisibilityStore());
const { showComponents } = storeToRefs(usePremiumStore());
const { isPackaged } = useInterop();
const { updateDarkMode } = useDarkMode();
const { load } = useDataLoader();

onMounted(async () => await load());
</script>

<template>
  <AppHost>
    <AppMessages>
      <ThemeChecker
        v-if="showComponents"
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
