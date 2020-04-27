<template>
  <div>
    <v-overlay v-if="!connected" class="account_management__loading">
      <v-row align="center" justify="center">
        <v-col cols="12" class="account_management__loading__content">
          <v-progress-circular indeterminate size="72"></v-progress-circular>
          <span class="account_management__loading__content__text">
            Please wait...
          </span>
        </v-col>
      </v-row>
    </v-overlay>
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
      v-if="connected"
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
      class="account_management__premium"
      action="Upgrade"
      :visible="!premium && !message && premiumVisible"
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
import MessageOverlay from '@/components/MessageOverlay.vue';
import { Version } from '@/store/store';
import { Credentials, UnlockPayload } from '@/typing/types';
import CreateAccount from './CreateAccount.vue';
import Login from './Login.vue';

const { mapState: mapSessionState } = createNamespacedHelpers('session');

@Component({
  components: {
    MessageOverlay,
    Login,
    CreateAccount
  },
  computed: {
    ...mapSessionState(['syncConflict', 'premium']),
    ...mapState(['version', 'message', 'connected']),
    ...mapGetters(['updateNeeded', 'message'])
  }
})
export default class AccountManagement extends Vue {
  accountCreation: boolean = false;
  premium!: boolean;
  loading: boolean = false;
  version!: Version;
  message!: boolean;
  connected!: boolean;
  syncConflict!: boolean;

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
      this.showPremiumDialog();
      this.showGetPremiumButton();
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
      this.showPremiumDialog();
    }
  }

  upgrade() {
    this.$interop.navigateToPremium();
    this.loginComplete();
  }

  dismiss() {
    this.premiumVisible = false;
  }

  private showPremiumDialog() {
    if (this.premium) {
      this.loginComplete();
      return;
    }
    this.premiumVisible = true;
  }

  private showGetPremiumButton() {
    this.$interop.premiumUserLoggedIn(this.premium);
  }

  closeUpdateDialog() {
    this.dismiss();
    this.premiumVisible = true;
  }
}
</script>

<style lang="scss">
.v-overlay {
  z-index: 8050 !important;
}

.v-dialog__content {
  z-index: 9999 !important;
}

.account_management {
  &__loading {
    &__content {
      align-items: center;
      justify-content: center;
      display: flex;
      flex-direction: column;
      &__text {
        margin-top: 48px;
        font-weight: 400;
        font-size: 26px;
      }
    }
  }
  &__privacy_notice {
    width: 100%;
    position: absolute;
    bottom: 20px;
    z-index: 8100;
    align-items: center;
    display: flex;
    flex-direction: column;

    &__message {
      text-align: center;
      max-width: 650px;
      font-size: 14px !important;
    }
  }
}

#privacy_notice__message {
  background: #e0e0e0 !important;
}
</style>
