<template>
  <v-app id="rotki">
    <div v-show="logged">
      <v-navigation-drawer
        v-model="drawer"
        width="300"
        fixed
        :clipped="$vuetify.breakpoint.mdAndUp"
        class="grey lighten-4"
        app
      >
        <div class="text-center">
          <img
            id="rotkehlchen_no_text"
            :src="require('./assets/images/rotkehlchen_no_text.png')"
            class="rotki__logo"
            alt=""
            @click="openSite()"
          />
        </div>
        <div class="text-center rotki__welcome-text font-weight-medium">
          Welcome {{ username }}
        </div>
        <navigation-menu></navigation-menu>
      </v-navigation-drawer>
      <v-app-bar app fixed clipped-left flat class="grey lighten-4">
        <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
        <v-toolbar-title class="font-weight-light rotki__version">
          Rotki {{ version }}
        </v-toolbar-title>
        <node-status-indicator></node-status-indicator>
        <balance-saved-indicator></balance-saved-indicator>
        <v-spacer></v-spacer>
        <update-indicator></update-indicator>
        <notification-indicator></notification-indicator>
        <progress-indicator></progress-indicator>
        <user-dropdown></user-dropdown>
        <currency-drop-down></currency-drop-down>
      </v-app-bar>
      <v-content v-if="logged">
        <router-view></router-view>
      </v-content>
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
import { createNamespacedHelpers, mapGetters, mapState } from 'vuex';
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

const { mapState: mapSessionState } = createNamespacedHelpers('session');

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
    ...mapSessionState(['logged', 'username']),
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
    }
  }

  drawer = true;

  startupError: string = '';

  openSite() {
    this.$interop.navigateToRotki();
  }

  dismiss() {
    this.$store.commit('resetMessage');
  }

  async created(): Promise<void> {
    this.$api.connect(4242);
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
.v-navigation-drawer--fixed {
  z-index: 100 !important;
}

.v-navigation-drawer--is-mobile {
  z-index: 200 !important;
}

.rotki__logo {
  max-height: 150px;
}

.rotki__version {
  margin-right: 16px;
}

#rotkehlchen_no_text {
  width: 150px;
  display: block;
  margin: 10px auto;
  padding: 15px;
}

.rotki__welcome-text {
  font-size: 18px;
  margin-top: 16px;
  margin-bottom: 20px;
}

::v-deep .v-content__wrap {
  border-top: #bcbcbc solid thin;
}
</style>
