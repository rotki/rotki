<template>
  <div>
    <v-overlay class="account_management__loading">
      <v-dialog :value="true && !premiumVisible" persistent max-width="450">
        <v-card class="rotki-welcome pb-6">
          <div
            class="pt-6 pb-3 display-3 font-weight-black primary white--text"
          >
            <span class="px-6">rotki</span>
            <span style="display: block;" class="pl-6 mb-3 caption">
              the opensource portfolio manager that respects your privacy
            </span>
          </div>
          <v-row
            v-if="!connected"
            no-gutters
            align="center"
            justify="center"
            class="my-3"
          >
            <v-col
              class="account_management__loading__content grey-darken-2--text"
            >
              <span
                class="account_management__loading__content__text my-3 pb-6"
              >
                Connecting to rotki backend
              </span>
              <v-progress-circular
                color="grey"
                indeterminate
                size="56"
              ></v-progress-circular>
            </v-col>
          </v-row>
          <v-slide-y-transition>
            <login
              :loading="loading"
              :displayed="!accountCreation && connected"
              :sync-conflict="syncConflict"
              @login="login($event)"
              @new-account="accountCreation = true"
            ></login>
          </v-slide-y-transition>
          <v-slide-y-transition>
            <create-account
              :loading="loading"
              :displayed="accountCreation && connected"
              @cancel="accountCreation = false"
              @confirm="createAccount($event)"
            ></create-account>
          </v-slide-y-transition>
        </v-card>
        <div class="account_management__privacy_notice">
          <v-alert
            id="privacy_notice__message"
            outlined
            dense
            color="primary"
            class="account_management__privacy_notice__message"
          >
            <div>rotki is a local application that respects your privacy.</div>
            <div>
              rotki accounts are encrypted using your password and saved in your
              local filesystem.
            </div>
          </v-alert>
        </div>
      </v-dialog>
    </v-overlay>

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

      rotki is open source software and needs your support! Please consider
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
@keyframes scrollLarge {
  0% {
    transform: rotate(-13deg) translateY(0);
  }
  100% {
    transform: rotate(-13deg) translateY(-1200px);
  }
}

.v-overlay {
  z-index: 200 !important;
}

.v-dialog__content {
  z-index: 9999 !important;
}

.account_management {
  &__loading {
    height: 400%;
    width: 400%;
    top: -40%;
    left: -100%;
    background-color: #42210b;
    background: url(~@/assets/images/rotkipattern2.png);
    -webkit-animation-name: scrollLarge;
    animation-name: scrollLarge;
    -webkit-animation-duration: 35s;
    animation-duration: 35s;
    -webkit-animation-timing-function: linear;
    animation-timing-function: linear;
    -webkit-animation-iteration-count: infinite;
    animation-iteration-count: infinite;

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
    max-width: 600px;
    position: absolute;
    left: 0;
    right: 0;
    margin-right: auto;
    margin-left: auto;
    bottom: 20px;
    z-index: -1;
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
