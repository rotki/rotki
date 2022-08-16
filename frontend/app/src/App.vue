<template>
  <v-app
    v-if="!isPlayground"
    id="rotki"
    class="app"
    :class="{ ['app--animations-disabled']: !animationsEnabled }"
  >
    <theme-checker v-if="premium" @update:dark-mode="updateDarkMode" />
    <app-update-popup />
    <div v-if="logged" class="app__content rotki-light-grey">
      <asset-update auto />
      <notification-popup />
      <v-navigation-drawer
        v-if="loginComplete"
        v-model="showDrawer"
        width="300"
        class="app__navigation-drawer"
        fixed
        :mini-variant="isMini"
        :color="appBarColor"
        clipped
        app
      >
        <div v-if="!isMini" class="text-center app__logo" />
        <div v-else class="app__logo-mini">
          {{ $t('app.name') }}
        </div>
        <navigation-menu :is-mini="isMini" />
        <v-spacer />
        <div
          v-if="!isMini"
          class="my-2 text-center px-2 app__navigation-drawer__version"
        >
          <span class="text-overline">
            <v-divider class="mx-3 my-1" />
            {{ appVersion }}
          </span>
        </div>
      </v-navigation-drawer>

      <v-app-bar
        app
        fixed
        clipped-left
        flat
        :color="appBarColor"
        class="app__app-bar"
      >
        <v-app-bar-nav-icon
          class="secondary--text text--lighten-4"
          @click="toggleDrawer()"
        />
        <div class="d-flex overflow-hidden">
          <sync-indicator />
          <global-search v-if="!xsOnly" />
          <back-button :can-navigate-back="canNavigateBack" />
        </div>
        <v-spacer />
        <div class="d-flex overflow-hidden fill-height align-center">
          <v-btn v-if="isDevelopment && !xsOnly" to="/playground" icon>
            <v-icon>mdi-crane</v-icon>
          </v-btn>
          <app-update-indicator />
          <pinned-indicator
            :visible="showPinned"
            @visible:update="showPinned = $event"
          />
          <theme-control v-if="!xsOnly" :dark-mode-enabled="darkModeEnabled" />
          <notification-indicator
            :visible="showNotificationBar"
            class="app__app-bar__button"
            @click="showNotificationBar = !showNotificationBar"
          />
          <currency-dropdown class="app__app-bar__button" />
          <privacy-mode-dropdown v-if="!xsOnly" class="app__app-bar__button" />
          <user-dropdown class="app__app-bar__button" />
          <help-indicator
            v-if="!xsOnly"
            :visible="showHelpBar"
            @visible:update="showHelpBar = $event"
          />
        </div>
      </v-app-bar>
      <notification-sidebar
        :visible="showNotificationBar"
        @close="showNotificationBar = false"
      />
      <help-sidebar
        :visible="showHelpBar"
        @visible:update="showHelpBar = $event"
        @about="showAbout = true"
      />
      <pinned-sidebar
        :visible="showPinned"
        @visible:update="showPinned = $event"
      />
      <div
        class="app-main"
        :class="{
          small: showDrawer && isMini,
          expanded: showDrawer && !isMini && !isMobile
        }"
      >
        <v-main>
          <router-view />
        </v-main>
      </div>
    </div>
    <message-dialog
      :title="message.title"
      :message="message.description"
      :success="message.success"
      @dismiss="dismissMessage()"
    />
    <startup-error-screen
      v-if="startupErrorMessage.length > 0"
      :message="startupErrorMessage"
      fatal
    />
    <mac-os-version-unsupported v-if="isMacOsVersionUnsupported" />
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
    <frontend-update-notifier v-if="!$interop.isPackaged" />
  </v-app>
  <dev-app v-else />
</template>

<script lang="ts">
import {
  computed,
  defineAsyncComponent,
  defineComponent,
  onBeforeMount,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { Chart, registerables } from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';
import { setupBackendManagement } from '@/composables/backend';
import { setupThemeCheck, useRoute, useRouter } from '@/composables/common';
import { getPremium, setupSession, useDarkMode } from '@/composables/session';
import { useInterop } from '@/electron-interop';
import { BackendCode } from '@/electron-main/backend-code';
import { ThemeChecker } from '@/premium/premium';
import { monitor } from '@/services/monitoring';
import { OverallPerformance } from '@/store/statistics/types';
import { useMainStore } from '@/store/store';
import { useStore } from '@/store/utils';
import { checkIfDevelopment } from '@/utils/env-utils';
import { logger } from '@/utils/logging';
import 'chartjs-adapter-moment';

export default defineComponent({
  name: 'App',
  components: {
    GlobalSearch: defineAsyncComponent(
      () => import('@/components/GlobalSearch.vue')
    ),
    FrontendUpdateNotifier: defineAsyncComponent(
      () => import('@/components/status/FrontendUpdateNotifier.vue')
    ),
    About: defineAsyncComponent(() => import('@/components/About.vue')),
    MacOsVersionUnsupported: defineAsyncComponent(
      () => import('@/components/error/MacOsVersionUnsupported.vue')
    ),
    AssetUpdate: defineAsyncComponent(
      () => import('@/components/status/update/AssetUpdate.vue')
    ),
    HelpIndicator: defineAsyncComponent(
      () => import('@/components/help/HelpIndicator.vue')
    ),
    HelpSidebar: defineAsyncComponent(
      () => import('@/components/help/HelpSidebar.vue')
    ),
    BackButton: defineAsyncComponent(
      () => import('@/components/helper/BackButton.vue')
    ),
    AppUpdatePopup: defineAsyncComponent(
      () => import('@/components/status/update/AppUpdatePopup.vue')
    ),
    StartupErrorScreen: defineAsyncComponent(
      () => import('@/components/error/StartupErrorScreen.vue')
    ),
    ThemeChecker,
    ThemeControl: defineAsyncComponent(
      () => import('@/components/premium/ThemeControl.vue')
    ),
    DevApp: defineAsyncComponent(() => import('@/DevApp.vue')),
    NotificationPopup: defineAsyncComponent(
      () => import('@/components/status/notifications/NotificationPopup.vue')
    ),
    NotificationSidebar: defineAsyncComponent(
      () => import('@/components/status/notifications/NotificationSidebar.vue')
    ),
    AccountManagement: defineAsyncComponent(
      () => import('@/components/AccountManagement.vue')
    ),
    AppUpdateIndicator: defineAsyncComponent(
      () => import('@/components/status/AppUpdateIndicator.vue')
    ),
    NotificationIndicator: defineAsyncComponent(
      () => import('@/components/status/NotificationIndicator.vue')
    ),
    SyncIndicator: defineAsyncComponent(
      () => import('@/components/status/sync/SyncIndicator.vue')
    ),
    MessageDialog: defineAsyncComponent(
      () => import('@/components/dialogs/MessageDialog.vue')
    ),
    CurrencyDropdown: defineAsyncComponent(
      () => import('@/components/CurrencyDropdown.vue')
    ),
    NavigationMenu: defineAsyncComponent(
      () => import('@/components/NavigationMenu.vue')
    ),
    UserDropdown: defineAsyncComponent(
      () => import('@/components/UserDropdown.vue')
    ),
    PrivacyModeDropdown: defineAsyncComponent(
      () => import('@/components/PrivacyModeDropdown.vue')
    ),
    PinnedIndicator: defineAsyncComponent(
      () => import('@/components/PinnedIndicator.vue')
    ),
    PinnedSidebar: defineAsyncComponent(
      () => import('@/components/PinnedSidebar.vue')
    )
  },
  setup() {
    const store = useMainStore();
    const { appVersion, message } = toRefs(store);
    const { setMessage, connect } = store;

    const { animationsEnabled } = setupSession();

    const showNotificationBar = ref(false);
    const showHelpBar = ref(false);
    const showPinned = ref(false);
    const showAbout = ref(false);
    const showDrawer = ref(false);
    const isMini = ref(false);
    const startupErrorMessage = ref('');
    const isMacOsVersionUnsupported = ref(false);

    const { navigateToRotki, onError, onAbout, updateTray, onRestart } =
      useInterop();
    const openSite = navigateToRotki;
    const dismissMessage = () => setMessage();
    const toggleDrawer = () => {
      if (!get(showDrawer)) {
        set(showDrawer, !get(showDrawer));
        set(isMini, false);
      } else {
        set(isMini, !get(isMini));
      }
    };

    const { isMobile, dark, currentBreakpoint } = setupThemeCheck();
    const xsOnly = computed(() => get(currentBreakpoint).xsOnly);

    const route = useRoute();
    const router = useRouter();

    const canNavigateBack = computed(() => {
      const canNavigateBack = get(route).meta?.canNavigateBack ?? false;
      return canNavigateBack && window.history.length > 1;
    });

    const isDevelopment = checkIfDevelopment();
    const isPlayground = computed(() => {
      return isDevelopment && get(route).name === 'playground';
    });

    const appBarColor = computed(() => {
      if (!get(dark)) {
        return 'white';
      }
      return null;
    });

    const { commit, state, getters } = useStore();

    const logged = computed(() => state.session?.logged ?? false);
    const username = computed(() => state.session?.username ?? '');
    const loginComplete = computed(() => state.session?.loginComplete ?? false);
    const loginIn = computed(() => get(logged) && get(loginComplete));
    const overall = computed<OverallPerformance>(
      () => getters['statistics/overall']
    );

    const completeLogin = async (complete: boolean) => {
      await commit('session/completeLogin', complete, { root: true });
    };

    const { restartBackend } = setupBackendManagement();

    onBeforeMount(async () => {
      onError((backendOutput: string | Error, code: BackendCode) => {
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
      });
      onAbout(() => set(showAbout, true));
      onRestart(async () => {
        set(startupErrorMessage, '');
        await restartBackend();
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

    onBeforeMount(() => {
      Chart.defaults.font.family = 'Roboto';
      Chart.register(...registerables);
      Chart.register(zoomPlugin);
    });

    watch(overall, overall => {
      if (overall.percentage === '-') {
        return;
      }
      updateTray(overall);
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

    const premium = getPremium();

    const { pinned } = setupSession();

    watch(pinned, (current, prev) => {
      if (current !== prev) {
        set(showPinned, !!current);
      }
    });

    return {
      animationsEnabled,
      username,
      premium,
      loginIn,
      logged,
      loginComplete,
      appVersion,
      message,
      showDrawer,
      showNotificationBar,
      showAbout,
      showHelpBar,
      showPinned,
      isMini,
      startupErrorMessage,
      isMacOsVersionUnsupported,
      isMobile,
      xsOnly,
      appBarColor,
      canNavigateBack,
      isDevelopment,
      isPlayground,
      dismissMessage,
      completeLogin,
      openSite,
      toggleDrawer,
      ...useDarkMode()
    };
  }
});
</script>

<style scoped lang="scss">
.v-navigation-drawer {
  &--is-mobile {
    padding-top: 60px !important;
  }
}

::v-deep {
  .v-navigation-drawer {
    box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1);

    &__border {
      background-color: transparent !important;
    }
  }

  .v-main {
    padding: 0 !important;
  }

  .v-app-bar {
    &::after {
      height: 1px;
      display: block;
      width: 100%;
      content: '';
      border-bottom: var(--v-rotki-light-grey-darken1) solid thin;
    }
  }
}

.app {
  overflow: hidden;

  &--animations-disabled {
    ::v-deep {
      * {
        &:not(.animate) {
          // ignore manual animation (e.g. animation on login screen)

          &,
          &::before,
          &::after {
            animation-timing-function: steps(5, end) !important;
          }
        }
      }
    }
  }

  &__app-bar {
    ::v-deep {
      .v-toolbar {
        &__content {
          padding: 0 1rem;
        }
      }
    }

    &__button {
      i {
        &:focus {
          color: var(--v-primary-base) !important;
        }
      }

      button {
        &:focus {
          color: var(--v-primary-base) !important;
        }
      }
    }
  }

  &__logo {
    min-height: 150px;
    margin-bottom: 15px;
    margin-top: 15px;
    background: url(/assets/images/rotkehlchen_no_text.png) no-repeat center;
    background-size: contain;
  }

  &__logo-mini {
    text-align: center;
    align-self: center;
    font-size: 3em;
    font-weight: bold;
    height: 150px;
    width: 64px;
    writing-mode: vertical-lr;
    transform: rotate(-180deg);
    margin-bottom: 15px;
    margin-top: 15px;
  }

  &__navigation-drawer {
    padding-bottom: 48px;

    &__version {
      position: fixed;
      bottom: 0;
      width: 100%;
    }
  }

  &-main {
    padding-top: 1rem;
    padding-bottom: 1rem;
    width: 100%;
    min-height: calc(100vh - 64px);

    &.small {
      padding-left: 56px;
    }

    &.expanded {
      padding-left: 300px;
    }
  }
}
</style>
