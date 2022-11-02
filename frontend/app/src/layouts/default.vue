<template>
  <app-host>
    <app-messages
      :startup-error="startupErrorMessage"
      :macos-unsupported="isMacOsVersionUnsupported"
      :win-unsupported="isWinVersionUnsupported"
    >
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
import { useBackendManagement } from '@/composables/backend';
import { useTheme } from '@/composables/common';
import { useDarkMode } from '@/composables/dark-mode';
import { useInterop } from '@/electron-interop';
import { BackendCode } from '@/electron-main/backend-code';
import { ThemeChecker } from '@/premium/premium';
import { useMainStore } from '@/store/main';
import { useMonitorStore } from '@/store/monitor';
import { useSessionStore } from '@/store/session';
import { usePremiumStore } from '@/store/session/premium';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { checkIfDevelopment } from '@/utils/env-utils';
import { logger } from '@/utils/logging';

const startupErrorMessage = ref('');
const isMacOsVersionUnsupported = ref(false);
const isWinVersionUnsupported = ref(false);

const { connect } = useMainStore();
const { showAbout, showDrawer } = storeToRefs(useAreaVisibilityStore());
const { logged, loginComplete } = storeToRefs(useSessionStore());
const { showComponents } = storeToRefs(usePremiumStore());
const { setupListeners, isPackaged } = useInterop();
const { isMobile } = useTheme();
const { updateDarkMode } = useDarkMode();

const router = useRouter();
const route = useRoute();

const isDevelopment = checkIfDevelopment();

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
  } else {
    set(showDrawer, !get(isMobile));
  }

  if (get(route).name !== 'dashboard') {
    await router.push({ name: 'dashboard' });
  }
});
</script>
