<template>
  <app-host>
    <app-messages
      :startup-error="startupErrorMessage"
      :macos-unsupported="isMacOsVersionUnsupported"
      :win-unsupported="isWinVersionUnsupported"
    >
      <account-management />
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
import AccountManagement from '@/components/user/LoginHost.vue';
import { useBackendManagement } from '@/composables/backend';
import { useSessionStateCleaner } from '@/composables/logout';
import { useInterop } from '@/electron-interop';
import { BackendCode } from '@/electron-main/backend-code';
import { Routes } from '@/router/routes';
import { useMainStore } from '@/store/main';
import { useMonitorStore } from '@/store/monitor';
import { useSessionAuthStore } from '@/store/session/auth';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { checkIfDevelopment } from '@/utils/env-utils';
import { logger } from '@/utils/logging';

const startupErrorMessage = ref('');
const isMacOsVersionUnsupported = ref(false);
const isWinVersionUnsupported = ref(false);

const { connect } = useMainStore();
const { showAbout } = storeToRefs(useAreaVisibilityStore());
const { logged, loginComplete } = storeToRefs(useSessionAuthStore());
const { setupListeners, isPackaged } = useInterop();

const router = useRouter();
const route = useRoute();

const isDevelopment = checkIfDevelopment();
useSessionStateCleaner();

const completeLogin = async (complete: boolean) => {
  set(loginComplete, complete);
};

const { restartBackend } = useBackendManagement();
const { start } = useMonitorStore();
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
      } else if (code === BackendCode.WIN_VERSION) {
        set(isWinVersionUnsupported, true);
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
    start();
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
  }

  if (get(route).path !== Routes.DASHBOARD) {
    await router.push(Routes.DASHBOARD);
  }
});
</script>
