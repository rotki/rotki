<template>
  <div>
    <v-overlay
      class="account-management__loading"
      color="grey lighten-4"
      opacity="0.8"
    >
      <v-dialog :value="!premiumVisible" persistent max-width="450">
        <v-card class="account-management__card pb-6">
          <div
            class="pt-6 pb-3 display-3 font-weight-black white--text account-management__card__title"
          >
            <span class="px-6">rotki</span>
            <span class="d-block mb-3 pl-6 text-caption">
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
              class="account-management__loading__content grey-darken-1--text"
            >
              <span
                class="account-management__loading__content__text my-3 pb-6"
              >
                Connecting to rotki backend
              </span>
              <v-progress-circular color="grey" indeterminate size="56" />
            </v-col>
          </v-row>
          <v-slide-y-transition>
            <login
              :loading="loading"
              :displayed="!accountCreation && connected"
              :sync-conflict="syncConflict"
              @login="login($event)"
              @new-account="accountCreation = true"
            />
          </v-slide-y-transition>
          <v-slide-y-transition>
            <create-account
              :loading="loading"
              :displayed="accountCreation && connected"
              @cancel="accountCreation = false"
              @confirm="createAccount($event)"
            />
          </v-slide-y-transition>
        </v-card>
        <div class="account-management__privacy-notice">
          <v-alert
            outlined
            dense
            color="primary"
            class="account-management__privacy-notice__message"
          >
            <div>rotki is a local application that respects your privacy.</div>
            <div>
              rotki accounts are encrypted using your password and saved in your
              local filesystem.
            </div>
          </v-alert>
        </div>
      </v-dialog>

      <v-dialog
        :value="!premium && !!!message.title && premiumVisible"
        persistent
        max-width="450"
        @keydown.esc.stop="loginComplete()"
      >
        <v-card
          light
          max-width="500"
          class="mx-auto account-management__premium-dialog"
        >
          <v-card-title class="account-management__premium-dialog__title">
            Upgrade to Premium
          </v-card-title>
          <v-card-text>
            <v-row class="mx-auto text-justify">
              <v-col cols="2" align-self="center">
                <v-icon color="success" size="48">
                  fa fa-info-circle
                </v-icon>
              </v-col>
              <v-col cols="10">
                rotki is open source software and needs your support! Please
                consider upgrading to premium by purchasing a premium
                subscription. This way you can help us further develop the
                software and you can also enjoy additional premium-only
                features.
              </v-col>
            </v-row>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn
              color="primary"
              class="account-management__premium-dialog__buttons__cancel"
              depressed
              outlined
              @click="loginComplete()"
            >
              Close
            </v-btn>
            <v-btn
              color="primary"
              depressed
              class="account-management__premium-dialog__buttons__confirm"
              @click="upgrade()"
            >
              Upgrade
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-overlay>
  </div>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import CreateAccount from '@/components/account-management/CreateAccount.vue';
import Login from '@/components/account-management/Login.vue';
import { Message } from '@/store/types';
import { Credentials, UnlockPayload } from '@/typing/types';

@Component({
  components: {
    Login,
    CreateAccount
  },
  computed: {
    ...mapState('session', ['syncConflict', 'premium']),
    ...mapState(['message', 'connected']),
    ...mapGetters(['updateNeeded', 'message'])
  }
})
export default class AccountManagement extends Vue {
  accountCreation: boolean = false;
  premium!: boolean;
  loading: boolean = false;
  message!: Message;
  connected!: boolean;
  syncConflict!: boolean;

  premiumVisible = false;

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
    const {
      username,
      password,
      apiKey,
      apiSecret,
      submitUsageAnalytics
    } = credentials;
    this.loading = true;
    await this.$store.dispatch('session/unlock', {
      username,
      password,
      create: true,
      syncApproval: 'unknown',
      apiKey,
      apiSecret,
      submitUsageAnalytics
    } as UnlockPayload);
    this.loading = false;
    if (this.logged) {
      this.showGetPremiumButton();
      this.loginComplete();
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
}
</script>

<style scoped lang="scss">
@import '@/scss/scroll';
@keyframes scrollLarge {
  0% {
    transform: rotate(-13deg) translateY(0);
  }

  100% {
    transform: rotate(-13deg) translateY(-1200px);
  }
}

.v-overlay {
  z-index: 300 !important;
}

.v-dialog {
  &__content {
    z-index: 9999 !important;
  }
}

.account-management {
  &__card {
    max-height: 90vh;
    overflow: auto;

    &__title {
      background-color: var(--v-primary-base);
    }

    @extend .themed-scrollbar;
  }

  &__loading {
    height: 800%;
    width: 800%;
    top: -200% !important;
    left: -100% !important;
    background: white url(~@/assets/images/rotkipattern2.svg);
    background-size: 450px 150px;
    filter: grayscale(0.5);
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

  &__privacy-notice {
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
      background: #e0e0e0 !important;
    }
  }
}

::v-deep {
  .v-dialog {
    overflow-y: hidden;
  }
}
</style>
