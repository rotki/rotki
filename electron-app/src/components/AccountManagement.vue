<template>
  <div>
    <login
      :displayed="!message && !logged && !accountCreation"
      :loading="loading"
      @login="login($event)"
      @new-account="accountCreation = true"
    ></login>

    <create-account
      :loading="loading"
      :displayed="!message && !logged && accountCreation"
      @cancel="accountCreation = false"
      @confirm="createAccount($event)"
    ></create-account>

    <message-overlay
      :visible="!message && welcomeVisible"
      @close="closeWelcome()"
    >
      <template #title>
        Welcome to Rotki!
      </template>
      It appears this is your first time using the program. Follow the
      suggestions to integrate with some exchanges or manually input data.
    </message-overlay>

    <message-overlay
      action="Upgrade"
      :visible="!message && premiumVisible"
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
    ...mapState(['version', 'message']),
    ...mapGetters(['updateNeeded', 'message'])
  }
})
export default class AccountManagement extends Vue {
  accountCreation: boolean = false;
  newAccount!: boolean;
  loading: boolean = false;
  version!: Version;
  message!: boolean;

  private welcomeVisible = false;
  private premiumVisible = false;

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
    if (this.logged) {
      this.firstStep();
    }
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

  upgrade() {
    shell.openExternal('https://rotki.com/products/');
    this.dismiss();
  }

  dismiss() {
    this.welcomeVisible = false;
    this.premiumVisible = false;
  }

  private firstStep() {
    if (this.newAccount) {
      this.welcomeVisible = true;
    } else {
      this.premiumVisible = true;
    }
  }

  closeWelcome() {
    this.dismiss();
    this.premiumVisible = true;
  }

  closeUpdateDialog() {
    this.dismiss();
    this.premiumVisible = true;
  }
}
</script>
