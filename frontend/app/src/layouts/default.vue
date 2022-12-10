<template>
  <app-host>
    <app-messages>
      <theme-checker v-if="showComponents" @update:dark-mode="updateDarkMode" />
      <app-update-popup />
      <app-core />
    </app-messages>
    <v-dialog v-if="showAbout" v-model="showAbout" max-width="500">
      <about />
    </v-dialog>
    <frontend-update-notifier v-if="!isPackaged" />
  </app-host>
</template>

<script setup lang="ts">
import About from '@/components/About.vue';
import AppCore from '@/components/app/AppCore.vue';
import AppHost from '@/components/app/AppHost.vue';
import AppMessages from '@/components/app/AppMessages.vue';
import FrontendUpdateNotifier from '@/components/status/FrontendUpdateNotifier.vue';
import AppUpdatePopup from '@/components/status/update/AppUpdatePopup.vue';
import { ThemeChecker } from '@/premium/premium';
import { usePremiumStore } from '@/store/session/premium';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const { showAbout } = storeToRefs(useAreaVisibilityStore());
const { showComponents } = storeToRefs(usePremiumStore());
const { isPackaged } = useInterop();
const { updateDarkMode } = useDarkMode();
const { load } = useDataLoader();

onMounted(async () => await load());
</script>
