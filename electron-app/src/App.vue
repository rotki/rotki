<template>
  <div>
    <Transition name="fade-transition" mode="out-in">
      <div v-show="visibleModal" class="overlay"></div>
    </Transition>
    <nav
      class="navbar navbar-default navbar-static-top"
      role="navigation"
      style="margin-bottom: 0"
    >
      <div class="navbar-header">
        <button
          type="button"
          class="navbar-toggle"
          data-toggle="collapse"
          data-target=".navbar-collapse"
        >
          <span class="sr-only">Toggle navigation</span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
        </button>
        <a class="navbar-brand" href="">Rotkehlchen</a>
      </div>

      <ul class="nav navbar-top-links navbar-status-icons">
        <ul class="list-group lg-status-icons">
          <li class="list-group-item eth-node-status">
            <a class="eth-node-status-link" href="#">
              <i class="fa fa-link fa-fw"></i>
            </a>
            <ul class="dropdown-menu dropdown-eth-status alert-success">
              <p>Connected to a local ethereum node</p>
            </ul>
          </li>
          <li class="list-group-item balance-save-status">
            <a class="balances-saved-status-link" href="#">
              <i class="fa fa-save fa-fw"></i>
            </a>
            <ul class="dropdown-menu dropdown-balance-save-status">
              <p>
                Balances last saved:<br />
                <span id="last_balance_save_field">Never</span>
              </p>
            </ul>
          </li>
        </ul>
      </ul>
      <ul class="nav navbar-top-links navbar-right">
        <li class="dropdown">
          <a class="dropdown-toggle" data-toggle="dropdown" href="#">
            <i class="fa fa-bell fa-fw"></i> <i class="fa fa-caret-down"></i>
          </a>
          <ul class="dropdown-menu dropdown-alerts"></ul>
        </li>

        <li class="dropdown">
          <a class="dropdown-toggle" data-toggle="dropdown" href="#">
            <i
              id="top-loading-icon"
              class="fa fa-circle-o-notch fa-spin fa-fw"
            ></i>
            <i class="fa fa-caret-down"></i>
          </a>
          <ul class="dropdown-menu dropdown-tasks"></ul>
        </li>

        <user-dropdown></user-dropdown>
        <currency-drop-down></currency-drop-down>
      </ul>

      <div class="navbar-default sidebar" role="navigation">
        <div class="text-center">
          <img
            id="rotkehlchen_no_text"
            :src="require('./assets/images/rotkehlchen_no_text.png')"
            class="rounded"
            alt=""
          />
        </div>
        <div id="welcome_text" class="text-center"></div>
        <navigation-menu></navigation-menu>
      </div>
    </nav>

    <div id="page-wrapper">
      <router-view></router-view>
    </div>
    <confirmation
      v-if="logout"
      @confirm="logoutUser()"
      @cancel="cancelLogout()"
    ></confirmation>
    <message-dialog
      v-if="error"
      title="Login Failed"
      :message="error"
      @confirm="ok()"
    ></message-dialog>
    <login
      v-if="!userLogged && !error"
      @login="login($event)"
      @new-account="newAccount = true"
    ></login>
    <create-account
      v-if="newAccount"
      @cancel="newAccount = false"
      @confirm="createAccount($event)"
    ></create-account>
  </div>
</template>

<script lang="ts">
import './legacy/renderer';
import { Component, Vue } from 'vue-property-decorator';
import UserDropdown from '@/components/UserDropdown.vue';
import NavigationMenu from '@/components/NavigationMenu.vue';
import CurrencyDropDown from '@/components/CurrencyDropDown.vue';
import Confirmation from '@/components/Confirmation.vue';
import { mapState } from 'vuex';
import { reset_pages, settings } from '@/legacy/settings';
import { reset_total_balances } from '@/legacy/balances_table';
import { reset_tasks } from '@/legacy/monitor';
import { reset_exchange_tables } from '@/legacy/exchange';
import { reset_user_settings } from '@/legacy/user_settings';
import { create_or_reload_dashboard } from '@/legacy/dashboard';
import Login from '@/components/Login.vue';
import { AccountData, Credentials } from '@/typing/types';
import { handleUnlockResult } from '@/legacy/userunlock';
import MessageDialog from '@/components/MessageDialog.vue';
import CreateAccount from '@/components/CreateAccount.vue';
import { UnlockResult } from '@/model/action-result';

@Component({
  components: {
    CreateAccount,
    MessageDialog,
    Login,
    Confirmation,
    CurrencyDropDown,
    NavigationMenu,
    UserDropdown
  },
  computed: mapState(['logout', 'userLogged'])
})
export default class App extends Vue {
  logout!: boolean;
  userLogged!: boolean;

  newAccount: boolean = false;

  permissionNeeded: string = '';
  error: string = '';

  get visibleModal(): boolean {
    return this.logout;
  }

  created() {
    this.$rpc.connect();
  }

  ok() {
    this.error = '';
    this.permissionNeeded = '';
  }

  async login(credentials: Credentials) {
    this.$rpc
      .unlock_user(credentials.username, credentials.password)
      .then(unlockResult => this.completeLogin(unlockResult))
      .catch((reason: Error) => {
        this.error = reason.message;
      });
  }

  private completeLogin(unlockResult: UnlockResult) {
    this.newAccount = false;
    console.log(unlockResult);
    if (!unlockResult.result) {
      if (unlockResult.permission_needed) {
        this.permissionNeeded = unlockResult.message;
      } else {
        this.error = unlockResult.message;
      }
      return;
    }

    handleUnlockResult(unlockResult);
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
      .then(unlockResult => this.completeLogin(unlockResult))
      .catch((reason: Error) => {
        this.error = reason.message;
      });
  }

  logoutUser() {
    this.$rpc
      .logout()
      .then(() => {
        $('#welcome_text').html('');
        settings.reset();
        reset_total_balances();
        reset_pages();
        reset_tasks();
        reset_exchange_tables();
        reset_user_settings();
        $('#page-wrapper').html('');
        create_or_reload_dashboard();
        this.$store.commit('logout', false);
        this.$store.commit('logged', false);
      })
      .catch((reason: Error) => {
        console.log(`Error at logout`);
        console.error(reason);
      });
  }

  cancelLogout() {
    this.$store.commit('logout', false);
  }
}
</script>

<style lang="scss">
@import '~datatables.net-dt/css/jquery.dataTables.min.css';
</style>
