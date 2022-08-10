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

<script lang="ts">
import {
  computed,
  defineAsyncComponent,
  defineComponent,
  onBeforeMount,
  ref,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useBackendManagement } from '@/composables/backend';
import { useRoute, useRouter, useTheme } from '@/composables/common';
import { useDarkMode } from '@/composables/session';
import { useInterop } from '@/electron-interop';
import { BackendCode } from '@/electron-main/backend-code';
import i18n from '@/i18n';
import { ThemeChecker } from '@/premium/premium';
import { monitor } from '@/services/monitoring';
import { useMainStore } from '@/store/main';
import { useSessionStore } from '@/store/session';
import { usePremiumStore } from '@/store/session/premium';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { logger } from '@/utils/logging';
import 'chartjs-adapter-moment';

export default defineComponent({
  name: 'App',
  components: {
    AppHost: defineAsyncComponent(() => import('@/components/app/AppHost.vue')),
    AppMessages: defineAsyncComponent(
      () => import('@/components/app/AppMessages.vue')
    ),
    AppCore: defineAsyncComponent(() => import('@/components/app/AppCore.vue')),
    About: defineAsyncComponent(() => import('@/components/About.vue')),
    FrontendUpdateNotifier: defineAsyncComponent(
      () => import('@/components/status/FrontendUpdateNotifier.vue')
    ),
    AppUpdatePopup: defineAsyncComponent(
      () => import('@/components/status/update/AppUpdatePopup.vue')
    ),
    ThemeChecker,
    AccountManagement: defineAsyncComponent(
      () => import('@/components/AccountManagement.vue')
    )
  },
  setup() {
    const startupErrorMessage = ref('');
    const isMacOsVersionUnsupported = ref(false);

    const { connect } = useMainStore();
    const { showAbout, showDrawer } = storeToRefs(useAreaVisibilityStore());
    const { logged, username, loginComplete } = storeToRefs(useSessionStore());
    const { premium } = storeToRefs(usePremiumStore());
    const { setupListeners, isPackaged } = useInterop();
    const { isMobile } = useTheme();

    const router = useRouter();
    const route = useRoute();

    const isDevelopment = process.env.NODE_ENV === 'development';
    const loginIn = computed(() => get(logged) && get(loginComplete));

    const completeLogin = async (complete: boolean) => {
      set(loginComplete, complete);
    };

    const { restartBackend } = useBackendManagement();

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
            i18n
              .t('error.process_running', {
                pids: pids.join(', ')
              })
              .toString()
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

    return {
      username,
      loginIn,
      logged,
      loginComplete,
      startupErrorMessage,
      isMacOsVersionUnsupported,
      isPackaged,
      showAbout,
      premium,
      completeLogin,
      ...useDarkMode()
    };
  }
});
</script>
