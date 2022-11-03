<template>
  <app-host>
    <app-messages>
      <login-host />
    </app-messages>
    <v-dialog v-if="showAbout" v-model="showAbout" max-width="500">
      <about />
    </v-dialog>
    <frontend-update-notifier v-if="!isPackaged" />
  </app-host>
</template>

<script setup lang="ts">
import About from '@/components/About.vue';
import AppHost from '@/components/app/AppHost.vue';
import AppMessages from '@/components/app/AppMessages.vue';
import FrontendUpdateNotifier from '@/components/status/FrontendUpdateNotifier.vue';
import LoginHost from '@/components/user/LoginHost.vue';
import { useInterop } from '@/electron-interop';
import { Routes } from '@/router/routes';
import { useSessionAuthStore } from '@/store/session/auth';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const { showAbout } = storeToRefs(useAreaVisibilityStore());
const { logged, loginComplete } = storeToRefs(useSessionAuthStore());
const { isPackaged } = useInterop();

const router = useRouter();
const route = useRoute();

watch(logged, async logged => {
  if (!logged) {
    await set(loginComplete, false);
  }

  if (get(route).path !== Routes.DASHBOARD) {
    await router.push(Routes.DASHBOARD);
  }
});
</script>
