<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-app id="rotkehlchen">
    <v-navigation-drawer
      v-model="drawer"
      fixed
      :clipped="$vuetify.breakpoint.mdAndUp"
      class="grey lighten-4"
      app
    >
      <div class="text-center">
        <img
          id="rotkehlchen_no_text"
          :src="require('./assets/images/rotkehlchen_no_text.png')"
          class="logo"
          alt=""
          @click="openSite()"
        />
      </div>
      <div id="welcome_text" class="text-center"></div>
      <navigation-menu></navigation-menu>
    </v-navigation-drawer>
    <v-app-bar app fixed clipped-left>
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
      <v-toolbar-title class="font-weight-light">Rotkehlchen</v-toolbar-title>
      <node-status-indicator></node-status-indicator>
      <balance-saved-indicator></balance-saved-indicator>
      <v-spacer></v-spacer>
      <notification-indicator></notification-indicator>
      <progress-indicator></progress-indicator>
      <user-dropdown></user-dropdown>
      <currency-drop-down></currency-drop-down>
    </v-app-bar>
    <v-content v-if="logged">
      <router-view></router-view>
    </v-content>
    <confirm-dialog
      title="Confirmation Required"
      message="Are you sure you want to log out of your current rotkehlchen session?"
      :display="logout"
      @confirm="logoutUser()"
      @cancel="logout = false"
    ></confirm-dialog>
    <message-dialog
      v-if="message.title"
      :title="message.title"
      :message="message.description"
      @dismiss="dismiss()"
    ></message-dialog>
    <message-dialog
      v-if="startupError"
      title="Startup Error"
      :message="startupError"
      @dismiss="terminate()"
    ></message-dialog>
    <login
      :displayed="!logged && !message.title && !newAccount"
      @login="login($event)"
      @new-account="newAccount = true"
    ></login>
    <create-account
      :displayed="newAccount && !message.title"
      @cancel="newAccount = false"
      @confirm="createAccount($event)"
    ></create-account>
  </v-app>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import UserDropdown from '@/components/UserDropdown.vue';
import NavigationMenu from '@/components/NavigationMenu.vue';
import CurrencyDropDown from '@/components/CurrencyDropDown.vue';
import { createNamespacedHelpers, mapState } from 'vuex';
import Login from '@/components/Login.vue';
import { Credentials } from '@/typing/types';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import CreateAccount from '@/components/CreateAccount.vue';
import { monitor } from '@/services/monitoring';
import NodeStatusIndicator from '@/components/status/NodeStatusIndicator.vue';
import BalanceSavedIndicator from '@/components/status/BalanceSavedIndicator.vue';
import NotificationIndicator from '@/components/status/NotificationIndicator.vue';
import ProgressIndicator from '@/components/status/ProgressIndicator.vue';
import './services/task_manager';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { ipcRenderer, remote, shell } from 'electron';
import { UnlockPayload } from '@/store/session/actions';
import { Message } from '@/store/store';

const mapSessionState = createNamespacedHelpers('session').mapState;

@Component({
  components: {
    ProgressIndicator,
    NotificationIndicator,
    BalanceSavedIndicator,
    NodeStatusIndicator,
    CreateAccount,
    MessageDialog,
    Login,
    ConfirmDialog,
    CurrencyDropDown,
    NavigationMenu,
    UserDropdown
  },
  computed: {
    ...mapState(['message']),
    ...mapSessionState(['logged'])
  }
})
export default class App extends Vue {
  logout: boolean = false;
  logged!: boolean;
  message!: Message;

  newAccount: boolean = false;
  drawer = true;

  startupError: string = '';

  openSite() {
    shell.openExternal('http://rotkehlchen.io');
  }

  terminate() {
    remote.getCurrentWindow().close();
  }

  dismiss() {
    this.$store.commit('resetMessage');
  }

  created() {
    this.$rpc.connect();
    ipcRenderer.on('failed', () => {
      // get notified if the python subprocess dies
      this.startupError =
        'The Python backend crushed. Check rotkehlchen.log or open an issue in Github.';
      // send ack to main.
      ipcRenderer.send('ack', 1);
    });
  }

  ok() {
    this.error = '';
  }

  async login(credentials: Credentials) {
    const { username, password } = credentials;
    await this.$store.dispatch('session/unlock', {
      username: username,
      password: password
    } as UnlockPayload);
  }

  async createAccount(credentials: Credentials) {
    const { username, password } = credentials;
    await this.$store.dispatch('session/unlock', {
      username: username,
      password: password,
      create: true,
      syncApproval: 'unknown'
    } as UnlockPayload);
  }

  logoutUser() {
    this.$rpc
      .logout()
      .then(() => {
        monitor.stop();
        this.$store.commit('tasks/clear');
        this.$store.commit('session/logout');
      })
      .catch((reason: Error) => {
        console.log(`Error at logout`);
        console.error(reason);
      });
  }

  //   showInfo(
  //   'Welcome to Rotkehlchen!',
  //   'It appears this is your first time using the program. ' +
  //   'Follow the suggestions to integrate with some exchanges or manually input data.'
  // );
}
</script>

<style scoped lang="scss">
.logo {
  max-height: 150px;
}
#rotkehlchen_no_text {
  width: 150px;
  display: block;
  margin: 10px auto;
  padding: 15px;
  /* outline: 1px solid #e45325; */
}
</style>
