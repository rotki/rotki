<template>
  <v-app v-if="!isPlayground" id="rotki">
    <update-popup />
    <div v-if="logged" class="app__content rotki-light-grey">
      <notification-popup />
      <v-navigation-drawer
        v-if="loginComplete"
        v-model="drawer"
        width="300"
        class="app__navigation-drawer"
        fixed
        :mini-variant="mini"
        clipped
        app
      >
        <div v-if="!mini" class="text-center app__logo" />
        <div v-else class="app__logo-mini">
          {{ $t('app.name') }}
        </div>
        <navigation-menu :show-tooltips="mini" />
        <v-spacer />
        <div
          v-if="!mini"
          class="my-2 text-center px-2 app__navigation-drawer__version"
        >
          <span class="overline">
            <v-divider class="mx-3 my-1" />
            {{ version }}
          </span>
        </div>
      </v-navigation-drawer>

      <v-app-bar app fixed clipped-left flat color="white" class="app__app-bar">
        <v-app-bar-nav-icon
          class="secondary--text text--lighten-2"
          @click="toggleDrawer()"
        />
        <node-status-indicator />
        <balance-saved-indicator />
        <v-spacer />
        <update-indicator />
        <notification-indicator
          :visible="notifications"
          class="app__app-bar__button"
          @click="notifications = !notifications"
        />
        <progress-indicator class="app__app-bar__button" />
        <currency-drop-down class="red--text app__app-bar__button" />
        <user-dropdown class="app__app-bar__button" />
      </v-app-bar>
      <notification-sidebar
        :visible="notifications"
        @close="notifications = false"
      />
      <v-main v-if="logged" class="fill-height">
        <router-view />
      </v-main>
    </div>
    <message-dialog
      :title="message.title"
      :message="message.description"
      :success="message.success"
      @dismiss="dismiss()"
    />
    <startup-error-screen
      v-if="startupError.length > 0"
      :message="startupError"
      fatal
    />
    <v-fade-transition>
      <account-management
        v-if="startupError.length === 0 && !loginIn"
        :logged="logged"
        @login-complete="completeLogin(true)"
      />
    </v-fade-transition>
  </v-app>
  <dev-app v-else />
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { mapGetters, mapMutations, mapState } from 'vuex';
import AccountManagement from '@/components/AccountManagement.vue';
import CurrencyDropDown from '@/components/CurrencyDropDown.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import StartupErrorScreen from '@/components/error/StartupErrorScreen.vue';
import NavigationMenu from '@/components/NavigationMenu.vue';
import NodeStatusIndicator from '@/components/status/NodeStatusIndicator.vue';
import NotificationIndicator from '@/components/status/NotificationIndicator.vue';
import NotificationPopup from '@/components/status/notifications/NotificationPopup.vue';
import NotificationSidebar from '@/components/status/notifications/NotificationSidebar.vue';
import ProgressIndicator from '@/components/status/ProgressIndicator.vue';
import SyncIndicator from '@/components/status/sync/SyncIndicator.vue';
import '@/services/task-manager';
import UpdatePopup from '@/components/status/update/UpdatePopup.vue';
import UpdateIndicator from '@/components/status/UpdateIndicator.vue';
import UserDropdown from '@/components/UserDropdown.vue';
import DevApp from '@/DevApp.vue';
import { monitor } from '@/services/monitoring';
import { Message } from '@/store/types';

@Component({
  components: {
    UpdatePopup,
    StartupErrorScreen,
    DevApp,
    NotificationPopup,
    NotificationSidebar,
    ErrorScreen,
    AccountManagement,
    UpdateIndicator,
    ProgressIndicator,
    NotificationIndicator,
    BalanceSavedIndicator: SyncIndicator,
    NodeStatusIndicator,
    MessageDialog,
    CurrencyDropDown,
    NavigationMenu,
    UserDropdown
  },
  computed: {
    ...mapState(['message']),
    ...mapState('session', ['logged', 'username', 'loginComplete']),
    ...mapGetters(['version'])
  },
  methods: {
    ...mapMutations('session', ['completeLogin'])
  }
})
export default class App extends Vue {
  logged!: boolean;
  message!: Message;
  version!: string;

  loginComplete!: boolean;
  completeLogin!: (complete: boolean) => void;

  notifications: boolean = false;

  get loginIn(): boolean {
    return this.logged && this.loginComplete;
  }

  @Watch('logged')
  onLoggedChange() {
    if (!this.logged) {
      this.completeLogin(false);
    } else {
      this.drawer = !this.$vuetify.breakpoint.mobile;
    }

    if (this.$route.name !== 'dashboard') {
      this.$router.push({ name: 'dashboard' });
    }
  }

  drawer = false;
  mini = false;

  startupError: string = '';

  openSite() {
    this.$interop.navigateToRotki();
  }

  dismiss() {
    this.$store.commit('resetMessage');
  }

  toggleDrawer() {
    if (!this.drawer) {
      this.drawer = !this.drawer;
      this.mini = false;
    } else {
      this.mini = !this.mini;
    }
  }

  async created(): Promise<void> {
    await this.$store.dispatch('connect');
    await this.$store.dispatch('version');
    this.$interop.onError((backendOutput: string) => {
      this.startupError = backendOutput;
    });

    if (process.env.NODE_ENV === 'development' && this.logged) {
      monitor.start();
    }
  }

  get isPlayground(): boolean {
    return (
      process.env.NODE_ENV === 'development' &&
      this.$route.name === 'playground'
    );
  }
}
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

::v-deep {
  .v-navigation-drawer {
    background: #ffffff;
    box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1);

    &__border {
      background-color: transparent !important;
    }
  }

  .v-main {
    overflow-y: scroll;
    margin-top: 64px;
    padding-top: 0 !important;
    height: calc(100vh - 64px);

    &__wrap {
      padding-left: 25px;
    }
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
