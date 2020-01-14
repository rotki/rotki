<template>
  <div>
    <div class="account_management__privacy_notice">
      <v-alert
        id="privacy_notice__message"
        outlined
        dense
        color="primary"
        class="account_management__privacy_notice__message"
      >
        <div>Rotki is a local application that respects your privacy.</div>
        <div>
          Rotki accounts are encrypted using your password and saved in your
          local filesystem.
        </div>
      </v-alert>
    </div>
    <login
      :displayed="!message && !logged && !accountCreation"
      :loading="loading"
      :sync-conflict="syncConflict"
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
      @close="loginComplete"
    >
      <template #title>
        Upgrade to Premium
      </template>

      Rotki is open source software and needs your support! Please consider
      upgrading to premium by purchasing a premium subscription. This way you
      can help us further develop the software and you can also enjoy additional
      premium-only features.
    </message-overlay>
  </div>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers, mapGetters, mapState } from 'vuex';
import Login from './Login.vue';
import CreateAccount from './CreateAccount.vue';
import { Credentials, UnlockPayload } from '@/typing/types';
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
    ...mapSessionState(['newAccount', 'syncConflict']),
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
  syncConflict!: boolean;

  private welcomeVisible = false;
  private premiumVisible = false;

  @Prop({ required: true, type: Boolean })
  logged!: boolean;

  @Emit()
  loginComplete() {
    this.dismiss();
  }

  async login(credentials: Credentials) {
    const { username, password, syncApproval } = credentials;
    this.loading = true;
    await this.$store.dispatch('session/unlock', {
      username,
      password,
      syncApproval
    } as UnlockPayload);
    this.loading = false;
    if (this.logged) {
      this.firstStep();
    }
  }

  async createAccount(credentials: Credentials) {
    const { username, password, apiKey, apiSecret } = credentials;
    this.loading = true;
    await this.$store.dispatch('session/unlock', {
      username,
      password,
      create: true,
      syncApproval: 'unknown',
      apiKey,
      apiSecret
    } as UnlockPayload);
    this.loading = false;
    if (this.logged) {
      this.firstStep();
    }
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

<style lang="scss">
.account_management__privacy_notice {
  width: 100%;
  position: absolute;
  bottom: 20px;
  z-index: 9999;
  align-items: center;
  display: flex;
  flex-direction: column;

  &__message {
    text-align: center;
    max-width: 650px;
    font-size: 14px !important;
  }
}

#privacy_notice__message {
  background: #e0e0e0 !important;
}
</style>
