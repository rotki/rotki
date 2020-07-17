<template>
  <v-app id="rotki">
    <div :show="logged" class="app__content rotki-light-grey">
      <v-navigation-drawer
        v-model="drawer"
        width="300"
        class="app__navigation-drawer"
        fixed
        :mini-variant="mini"
        clipped
        app
      >
        <div v-if="!mini" class="text-center app__logo"></div>
        <div v-else class="app__logo-mini">
          rotki
        </div>
        <navigation-menu :show-tooltips="mini"></navigation-menu>
        <v-spacer></v-spacer>
        <div
          v-if="!mini"
          class="my-2 text-center px-2 app__navigation-drawer__version"
        >
          <span class="overline">
            <v-divider class="mx-3 my-1"></v-divider>
            {{ version }}
          </span>
        </div>
      </v-navigation-drawer>
      <v-app-bar app fixed clipped-left flat color="white" class="app__app-bar">
        <v-app-bar-nav-icon
          class="secondary--text text--lighten-2"
          @click="toggleDrawer()"
        ></v-app-bar-nav-icon>
        <node-status-indicator></node-status-indicator>
        <balance-saved-indicator></balance-saved-indicator>
        <v-spacer></v-spacer>
        <update-indicator></update-indicator>
        <notification-indicator
          class="app__app-bar__button"
        ></notification-indicator>
        <progress-indicator class="app__app-bar__button"></progress-indicator>
        <currency-drop-down
          class="red--text app__app-bar__button"
        ></currency-drop-down>
        <user-dropdown class="app__app-bar__button"></user-dropdown>
      </v-app-bar>
      <v-main v-if="logged" class="fill-height">
        <router-view></router-view>
      </v-main>
    </div>
    <message-dialog
      :title="message.title"
      :message="message.description"
      :success="message.success"
      @dismiss="dismiss()"
    ></message-dialog>
    <error-screen
      v-if="startupError.length > 0"
      :message="startupError"
    ></error-screen>
    <v-fade-transition>
      <account-management
        v-if="startupError.length === 0 && !loginIn"
        :logged="logged"
        @login-complete="loginComplete = true"
      ></account-management>
    </v-fade-transition>
  </v-app>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import AccountManagement from '@/components/AccountManagement.vue';
import CurrencyDropDown from '@/components/CurrencyDropDown.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import NavigationMenu from '@/components/NavigationMenu.vue';
import BalanceSavedIndicator from '@/components/status/BalanceSavedIndicator.vue';
import NodeStatusIndicator from '@/components/status/NodeStatusIndicator.vue';
import NotificationIndicator from '@/components/status/NotificationIndicator.vue';
import ProgressIndicator from '@/components/status/ProgressIndicator.vue';
import '@/services/task-manager';
import UpdateIndicator from '@/components/status/UpdateIndicator.vue';
import UserDropdown from '@/components/UserDropdown.vue';
import ErrorScreen from '@/ErrorScreen.vue';
import { Message } from '@/store/store';

@Component({
  components: {
    ErrorScreen,
    AccountManagement,
    UpdateIndicator,
    ProgressIndicator,
    NotificationIndicator,
    BalanceSavedIndicator,
    NodeStatusIndicator,
    MessageDialog,
    ConfirmDialog,
    CurrencyDropDown,
    NavigationMenu,
    UserDropdown
  },
  computed: {
    ...mapState(['message']),
    ...mapState('session', ['logged', 'username']),
    ...mapGetters(['version'])
  }
})
export default class App extends Vue {
  logged!: boolean;
  message!: Message;
  version!: string;

  loginComplete: boolean = false;

  get loginIn(): boolean {
    return this.logged && this.loginComplete;
  }

  @Watch('logged')
  onLoggedChange() {
    if (!this.logged) {
      this.loginComplete = false;
    } else {
      this.$router.push({ name: 'dashboard' });
    }
  }

  drawer = true;
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
    this.$interop.onError(() => {
      this.startupError =
        'The Python backend crashed. Check rotkehlchen.log or open an issue in Github.';
    });
  }
}
</script>

<style scoped lang="scss">
@import '@/scss/scroll';

.v-navigation-drawer {
  &--fixed {
    z-index: 100 !important;
  }

  &--is-mobile {
    padding-top: 60px;
    z-index: 300 !important;
  }

  @extend .themed-scrollbar;
}

.app {
  &__app-bar {
    z-index: 2015;

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
    box-shadow: 14px 0 10px -10px var(--v-rotki-light-grey-darken1);
    z-index: 200 !important;
    padding-bottom: 48px;

    &__version {
      position: fixed;
      bottom: 0;
      width: 100%;
    }
  }
}

::v-deep {
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
