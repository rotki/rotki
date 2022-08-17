<template>
  <app-host>
    <app-messages
      :startup-error="startupErrorMessage"
      :macos-unsupported="isMacOsVersionUnsupported"
    >
      <theme-checker v-if="premium" @update:dark-mode="updateDarkMode" />
      <app-update-popup />
      <app-core v-if="logged" />
    </app-messages>

    <v-fade-transition>
      <account-management
        v-if="startupErrorMessage.length === 0 && !loginIn"
        :logged="logged"
        @login-complete="completeLogin(true)"
        @about="showAbout = true"
      />
    </v-fade-transition>
    <v-dialog v-if="showAbout" v-model="showAbout" max-width="500">
      <about />
    </v-dialog>
    <frontend-update-notifier v-if="!isPackaged" />
  </app-host>
</template>

<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  onBeforeMount,
  ref,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import { useBackendManagement } from '@/composables/backend';
import { useRoute, useRouter, useTheme } from '@/composables/common';
import { useDarkMode } from '@/composables/session';
import { useInterop } from '@/electron-interop';
import { BackendCode } from '@/electron-main/backend-code';
import { ThemeChecker } from '@/premium/premium';
import { monitor } from '@/services/monitoring';
import { useMainStore } from '@/store/main';
import { useSessionStore } from '@/store/session';
import { usePremiumStore } from '@/store/session/premium';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { checkIfDevelopment } from '@/utils/env-utils';
import { logger } from '@/utils/logging';
import 'chartjs-adapter-moment';

const AppHost = defineAsyncComponent(
  () => import('@/components/app/AppHost.vue')
);
const AppMessages = defineAsyncComponent(
  () => import('@/components/app/AppMessages.vue')
);
const AppCore = defineAsyncComponent(
  () => import('@/components/app/AppCore.vue')
);
const About = defineAsyncComponent(() => import('@/components/About.vue'));
const FrontendUpdateNotifier = defineAsyncComponent(
  () => import('@/components/status/FrontendUpdateNotifier.vue')
);
const AppUpdatePopup = defineAsyncComponent(
  () => import('@/components/status/update/AppUpdatePopup.vue')
);
const AccountManagement = defineAsyncComponent(
  () => import('@/components/AccountManagement.vue')
);

const startupErrorMessage = ref('');
const isMacOsVersionUnsupported = ref(false);

const { connect } = useMainStore();
const { showAbout, showDrawer } = storeToRefs(useAreaVisibilityStore());
const { logged, loginComplete } = storeToRefs(useSessionStore());
const { premium } = storeToRefs(usePremiumStore());
const { setupListeners, isPackaged } = useInterop();
const { isMobile } = useTheme();
const { updateDarkMode } = useDarkMode();

const router = useRouter();
const route = useRoute();

const isDevelopment = checkIfDevelopment();
const loginIn = computed(() => get(logged) && get(loginComplete));

const completeLogin = async (complete: boolean) => {
  set(loginComplete, complete);
};

const { restartBackend } = useBackendManagement();
const { t } = useI18n();

onBeforeMount(async () => {
  setupListeners({
    onError: (backendOutput: string | Error, code: BackendCode) => {
      logger.error(backendOutput, code);
      if (code === BackendCode.TERMINATED) {
        const message =
          typeof backendOutput === 'string'
            ? backendOutput
            : backendOutput.message;
        set(startupErrorMessage, message);
      } else if (code === BackendCode.MACOS_VERSION) {
        set(isMacOsVersionUnsupported, true);
      }
    },
    onAbout: () => set(showAbout, true),
    onRestart: async () => {
      set(startupErrorMessage, '');
      await restartBackend();
    },
    onProcessDetected: pids => {
      set(
        startupErrorMessage,
        t('error.process_running', {
          pids: pids.join(', ')
        }).toString()
      );
    }
  });

  await connect();
  if (isDevelopment && get(logged)) {
    monitor.start();
  }
  const search = window.location.search;
  const skipUpdate = search.indexOf('skip_update') >= 0;
  if (skipUpdate) {
    sessionStorage.setItem('skip_update', '1');
  }
});

watch(logged, async logged => {
  if (!logged) {
    await completeLogin(false);
  } else {
    set(showDrawer, !get(isMobile));
  }

  if (get(route).name !== 'dashboard') {
    router.push({ name: 'dashboard' });
  }
});
</script>
