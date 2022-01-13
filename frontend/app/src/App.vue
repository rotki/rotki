<template>
  <v-app v-if="!isPlayground" id="rotki" class="app">
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
        <navigation-menu :show-tooltips="isMini" />
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
          class="secondary--text text--lighten-2"
          @click="toggleDrawer()"
        />
        <node-status-indicator v-if="!isMobile" />
        <balance-saved-indicator />
        <back-button :can-navigate-back="canNavigateBack" />
        <v-spacer />
        <v-btn v-if="isDevelopment" to="/playground" icon>
          <v-icon>mdi-crane</v-icon>
        </v-btn>
        <app-update-indicator />
        <theme-switch v-if="premium" />
        <theme-switch-lock v-else />
        <notification-indicator
          :visible="showNotificationBar"
          class="app__app-bar__button"
          @click="showNotificationBar = !showNotificationBar"
        />
        <currency-drop-down class="red--text app__app-bar__button" />
        <user-dropdown class="app__app-bar__button" />
        <help-indicator
          v-if="!isMobile"
          :visible="showHelpBar"
          @visible:update="showHelpBar = $event"
        />
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
    <frontend-update-notifier />
  </v-app>
  <dev-app v-else />
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onBeforeMount,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import About from '@/components/About.vue';
import AccountManagement from '@/components/AccountManagement.vue';
import CurrencyDropDown from '@/components/CurrencyDropDown.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import MacOsVersionUnsupported from '@/components/error/MacOsVersionUnsupported.vue';
import StartupErrorScreen from '@/components/error/StartupErrorScreen.vue';
import HelpIndicator from '@/components/help/HelpIndicator.vue';
import HelpSidebar from '@/components/help/HelpSidebar.vue';
import BackButton from '@/components/helper/BackButton.vue';
import NavigationMenu from '@/components/NavigationMenu.vue';
import ThemeSwitchLock from '@/components/premium/ThemeSwitchLock.vue';
import AppUpdateIndicator from '@/components/status/AppUpdateIndicator.vue';
import FrontendUpdateNotifier from '@/components/status/FrontendUpdateNotifier.vue';
import NodeStatusIndicator from '@/components/status/NodeStatusIndicator.vue';
import NotificationIndicator from '@/components/status/NotificationIndicator.vue';
import NotificationPopup from '@/components/status/notifications/NotificationPopup.vue';
import NotificationSidebar from '@/components/status/notifications/NotificationSidebar.vue';
import SyncIndicator from '@/components/status/sync/SyncIndicator.vue';
import AppUpdatePopup from '@/components/status/update/AppUpdatePopup.vue';
import AssetUpdate from '@/components/status/update/AssetUpdate.vue';
import UserDropdown from '@/components/UserDropdown.vue';
import { setupThemeCheck, useRoute, useRouter } from '@/composables/common';
import { getPremium } from '@/composables/session';
import DevApp from '@/DevApp.vue';
import { useInterop } from '@/electron-interop';
import { BackendCode } from '@/electron-main/backend-code';
import { ThemeSwitch } from '@/premium/premium';
import { monitor } from '@/services/monitoring';
import { OverallPerformance } from '@/store/statistics/types';
import { useMainStore } from '@/store/store';
import { useStore } from '@/store/utils';
import { logger } from '@/utils/logging';

export default defineComponent({
  name: 'App',
  components: {
    FrontendUpdateNotifier,
    About,
    ThemeSwitchLock,
    MacOsVersionUnsupported,
    AssetUpdate,
    HelpIndicator,
    HelpSidebar,
    BackButton,
    AppUpdatePopup,
    StartupErrorScreen,
    ThemeSwitch,
    DevApp,
    NotificationPopup,
    NotificationSidebar,
    AccountManagement,
    AppUpdateIndicator,
    NotificationIndicator,
    BalanceSavedIndicator: SyncIndicator,
    NodeStatusIndicator,
    MessageDialog,
    CurrencyDropDown,
    NavigationMenu,
    UserDropdown
  },
  setup() {
    const store = useMainStore();
    const { appVersion, message } = toRefs(store);
    const { setMessage, connect } = store;

    const showNotificationBar = ref(false);
    const showHelpBar = ref(false);
    const showAbout = ref(false);
    const showDrawer = ref(false);
    const isMini = ref(false);
    const startupErrorMessage = ref('');
    const isMacOsVersionUnsupported = ref(false);

    const { navigateToRotki, onError, onAbout, updateTray } = useInterop();
    const openSite = navigateToRotki;
    const dismissMessage = () => setMessage();
    const toggleDrawer = () => {
      if (!showDrawer.value) {
        showDrawer.value = !showDrawer.value;
        isMini.value = false;
      } else {
        isMini.value = !isMini.value;
      }
    };

    const { isMobile, dark } = setupThemeCheck();

    const route = useRoute();
    const router = useRouter();

    const canNavigateBack = computed(() => {
      const canNavigateBack = route.value.meta?.canNavigateBack ?? false;
      return canNavigateBack && window.history.length > 1;
    });

    const isDevelopment = process.env.NODE_ENV === 'development';
    const isPlayground = computed(() => {
      return isDevelopment && route.value.name === 'playground';
    });

    const appBarColor = computed(() => {
      if (!dark.value) {
        return 'white';
      }
      return null;
    });

    const { commit, state, getters } = useStore();

    const logged = computed(() => state.session?.logged ?? false);
    const username = computed(() => state.session?.username ?? '');
    const loginComplete = computed(() => state.session?.loginComplete ?? false);
    const loginIn = computed(() => logged.value && loginComplete.value);
    const overall = computed<OverallPerformance>(
      () => getters['statistics/overall']
    );

    const completeLogin = async (complete: boolean) => {
      await commit('session/completeLogin', complete, { root: true });
    };

    onBeforeMount(async () => {
      onError((backendOutput: string, code: BackendCode) => {
        if (code === BackendCode.TERMINATED) {
          startupErrorMessage.value = backendOutput;
        } else if (code === BackendCode.MACOS_VERSION) {
          isMacOsVersionUnsupported.value = true;
        } else {
          logger.error(backendOutput, code);
        }
      });
      onAbout(() => (showAbout.value = true));

      await connect();
      if (isDevelopment && logged.value) {
        monitor.start();
      }
      const search = window.location.search;
      const skipUpdate = search.indexOf('skip_update') >= 0;
      if (skipUpdate) {
        sessionStorage.setItem('skip_update', '1');
      }
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
        showDrawer.value = !isMobile.value;
      }

      if (route.value.name !== 'dashboard') {
        router.push({ name: 'dashboard' });
      }
    });

    const premium = getPremium();

    return {
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
      isMini,
      startupErrorMessage,
      isMacOsVersionUnsupported,
      isMobile,
      appBarColor,
      canNavigateBack,
      isDevelopment,
      isPlayground,
      dismissMessage,
      completeLogin,
      openSite,
      toggleDrawer
    };
  }
});
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.v-navigation-drawer {
  &--is-mobile {
    padding-top: 60px !important;
  }

  @extend .themed-scrollbar;
}

.app {
  overflow: hidden;

  &__content {
    height: 100vh;
  }

  &__app-bar {
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
    background: url(~@/assets/images/rotkehlchen_no_text.png) no-repeat center;
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
}

.app-main {
  top: 64px;
  position: fixed;
  width: 100%;
  height: calc(100vh - 64px);
  overflow-y: scroll;
  overflow-x: hidden;
  scroll-behavior: smooth;

  &.small {
    left: 56px;
    width: calc(100vw - 56px);
  }

  &.expanded {
    left: 300px;
    width: calc(100vw - 300px);
  }

  @extend .themed-scrollbar;
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
</style>
