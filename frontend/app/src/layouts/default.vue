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
  <app-host>
    <app-messages>
      <theme-checker
        v-if="showComponents"
        @update:dark-mode="updateDarkMode($event)"
      />
      <app-update-popup />
      <app-core />
    </app-messages>
    <v-dialog v-if="showAbout" v-model="showAbout" max-width="500">
      <about />
    </v-dialog>
    <frontend-update-notifier v-if="!isPackaged" />
  </app-host>
</template>
