<script setup lang="ts">
import About from '@/components/About.vue';
import AppHost from '@/components/app/AppHost.vue';
import AppMessages from '@/components/app/AppMessages.vue';
import FrontendUpdateNotifier from '@/components/status/FrontendUpdateNotifier.vue';
import LoginHost from '@/components/user/LoginHost.vue';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const { showAbout } = storeToRefs(useAreaVisibilityStore());
const { isPackaged } = useInterop();
</script>

<template>
  <app-host>
    <frontend-update-notifier v-if="!isPackaged" />
    <app-messages>
      <login-host />
    </app-messages>
    <v-dialog v-if="showAbout" v-model="showAbout" max-width="500">
      <about />
    </v-dialog>
  </app-host>
</template>
