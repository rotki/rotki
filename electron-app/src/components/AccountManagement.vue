<template>
  <div>
    <login
      :displayed="!logged && !accountCreation"
      :loading="loading"
      @login="login($event)"
      @new-account="accountCreation = true"
    ></login>

    <create-account
      :loading="loading"
      :displayed="!logged && accountCreation"
      @cancel="accountCreation = false"
      @confirm="createAccount($event)"
    ></create-account>

    <message-overlay :visible="welcomeVisible" @close="closeWelcome()">
      <template #title>
        Welcome to Rotkehlchen!
      </template>
      It appears this is your first time using the program. Follow the
      suggestions to integrate with some exchanges or manually input data.
    </message-overlay>

    <message-overlay
      action="Download"
      :visible="versionVisible"
      @primary="download()"
      @close="closeUpdateDialog()"
    >
      <template #title>
        Version Update Available
      </template>

      Your Rotki version {{ version.version }} is outdated. The latest version
      is {{ version.latestVersion }} and it is available on Github. Press
      download to open the download link on your browser.
    </message-overlay>

    <message-overlay
      action="Upgrade"
      :visible="premiumVisible"
      @primary="upgrade()"
      @close="dismiss()"
    >
      <template #title>
        Upgrade to Premium
      </template>

      Rotki is open source software and need your support! Please consider
      upgrading to premium by purchasing a premium subscription. This way you
      can help us further develop the software and you can also enjoy additional
      premium-only features.
    </message-overlay>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers, mapGetters, mapState } from 'vuex';
import Login from './Login.vue';
import CreateAccount from './CreateAccount.vue';
import { Credentials } from '@/typing/types';
import { UnlockPayload } from '@/store/session/actions';
import MessageOverlay from '@/components/MessageOverlay.vue';
import { Version } from '@/store/store';
import { shell } from 'electron';

const { mapState: mapSessionState } = createNamespacedHelpers('session');

@Component({
  components: {
    MessageOverlay,
    Login,
    CreateAccount
  },
  computed: {
    ...mapSessionState(['newAccount']),
    ...mapState(['version']),
    ...mapGetters(['updateNeeded'])
  }
})
export default class AccountManagement extends Vue {
  accountCreation: boolean = false;
  newAccount!: boolean;
  loading: boolean = false;
  updateNeeded!: boolean;
  version!: Version;

  welcomeVisible: boolean = false;
  versionVisible: boolean = false;
  premiumVisible: boolean = false;

  @Prop({ required: true, type: Boolean })
  logged!: boolean;

  async login(credentials: Credentials) {
    const { username, password } = credentials;
    this.loading = true;
    await this.$store.dispatch('session/unlock', {
      username: username,
      password: password
    } as UnlockPayload);
    this.loading = false;
    this.firstStep();
  }

  async createAccount(credentials: Credentials) {
    const { username, password } = credentials;
    this.loading = true;
    await this.$store.dispatch('session/unlock', {
      username: username,
      password: password,
      create: true,
      syncApproval: 'unknown'
    } as UnlockPayload);
    this.loading = false;
    this.firstStep();
  }

  download() {
    shell.openExternal(this.version.url);
    this.closeUpdateDialog();
  }

  upgrade() {
    shell.openExternal('https://rotkehlchen.io/products/');
    this.dismiss();
  }

  dismiss() {
    this.welcomeVisible = false;
    this.versionVisible = false;
    this.premiumVisible = false;
  }

  private firstStep() {
    if (this.newAccount) {
      this.welcomeVisible = true;
    } else if (this.updateNeeded) {
      this.versionVisible = true;
    } else {
      this.premiumVisible = true;
    }
  }

  closeWelcome() {
    this.dismiss();
    if (this.updateNeeded) {
      this.versionVisible = true;
    } else {
      this.premiumVisible = true;
    }
  }

  closeUpdateDialog() {
    this.dismiss();
    this.premiumVisible = true;
  }
}
</script>
