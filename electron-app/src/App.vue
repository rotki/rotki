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
    <v-content v-if="userLogged">
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
      v-if="error"
      title="Login Failed"
      :message="error"
      @dismiss="ok()"
    ></message-dialog>
    <message-dialog
      v-if="startupError"
      title="Startup Error"
      :message="startupError"
      @dismiss="terminate()"
    ></message-dialog>
    <login
      :displayed="!userLogged && !error"
      @login="login($event)"
      @new-account="newAccount = true"
    ></login>
    <create-account
      :displayed="newAccount"
      @cancel="newAccount = false"
      @confirm="createAccount($event)"
    ></create-account>
    <sync-permission
      :displayed="permissionNeeded !== ''"
      :message="permissionNeeded"
    ></sync-permission>
  </v-app>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import UserDropdown from '@/components/UserDropdown.vue';
import NavigationMenu from '@/components/NavigationMenu.vue';
import CurrencyDropDown from '@/components/CurrencyDropDown.vue';
import { mapState } from 'vuex';
import Login from '@/components/Login.vue';
import { AccountData, Credentials } from '@/typing/types';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import CreateAccount from '@/components/CreateAccount.vue';
import { UnlockResult } from '@/model/action-result';
import SyncPermission from '@/components/dialogs/SyncPermission.vue';
import { monitor } from '@/services/monitoring';
import NodeStatusIndicator from '@/components/status/NodeStatusIndicator.vue';
import BalanceSavedIndicator from '@/components/status/BalanceSavedIndicator.vue';
import NotificationIndicator from '@/components/status/NotificationIndicator.vue';
import ProgressIndicator from '@/components/status/ProgressIndicator.vue';
import './services/task_manager';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { ipcRenderer, remote, shell } from 'electron';
import store from '@/store';
import { UnlockPayload } from '@/store/session/actions';

@Component({
  components: {
    ProgressIndicator,
    NotificationIndicator,
    BalanceSavedIndicator,
    NodeStatusIndicator,
    SyncPermission,
    CreateAccount,
    MessageDialog,
    Login,
    ConfirmDialog,
    CurrencyDropDown,
    NavigationMenu,
    UserDropdown
  },
  computed: mapState(['userLogged'])
})
export default class App extends Vue {
  logout: boolean = false;
  userLogged!: boolean;

  newAccount: boolean = false;
  drawer = true;

  permissionNeeded: string = '';
  error: string = '';
  startupError: string = '';

  private accountData?: AccountData;

  openSite() {
    shell.openExternal('http://rotkehlchen.io');
  }

  terminate() {
    remote.getCurrentWindow().close();
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
    this.permissionNeeded = '';
  }

  async confirmSync() {
    const accountData = this.accountData;
    if (!accountData) {
      throw new Error('no stored account');
    }

    await this.$store.dispatch('session/unlock', {
      username: accountData.username,
      password: accountData.password,
      create: true,
      syncApproval: 'yes',
      apiKey: accountData.apiKey,
      apiSecret: accountData.apiSecret
    } as UnlockPayload);
  }

  async cancelSync() {
    const accountData = this.accountData;
    if (!accountData) {
      throw new Error('no stored account');
    }

    await this.$store.dispatch('session/unlock', {
      username: accountData.username,
      password: accountData.password,
      create: true,
      syncApproval: 'no',
      apiKey: accountData.apiKey,
      apiSecret: accountData.apiSecret
    } as UnlockPayload);
  }

  async login(credentials: Credentials) {
    this.$rpc
      .unlock_user(credentials.username, credentials.password)
      .then(unlockResult => this.completeLogin(unlockResult))
      .catch((reason: Error) => {
        this.error = reason.message;
      });
  }

  private completeLogin(unlockResult: UnlockResult, accountData?: AccountData) {
    this.newAccount = false;
    if (!unlockResult.result) {
      if (unlockResult.permission_needed) {
        this.permissionNeeded = unlockResult.message;
        this.accountData = accountData;
      } else {
        this.error = unlockResult.message;
      }
      return;
    }

    (async function(response: UnlockResult, newUser: boolean = false) {
      const db_settings = response.settings;
      if (!db_settings) {
        throw new Error('Unlock Failed');
      }

      await store.dispatch('session/start', {
        premium: response.premium,
        settings: db_settings
      });

      monitor.start();
      await store.dispatch('balances/fetch', {
        newUser,
        exchanges: response.exchanges
      });
      store.commit('logged', true);
    })(unlockResult);
  }

  async createAccount(accountData: AccountData) {
    this.$rpc
      .unlock_user(
        accountData.username,
        accountData.password,
        true,
        'unknown',
        accountData.apiKey,
        accountData.apiSecret
      )
      .then(unlockResult => {
        this.$store.commit('newUser', true);
        this.completeLogin(unlockResult, accountData);
      })
      .catch((reason: Error) => {
        this.error = reason.message;
      });
  }

  logoutUser() {
    this.$rpc
      .logout()
      .then(() => {
        monitor.stop();
        this.$store.commit('tasks/clear');
        this.$store.commit('logout');
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
