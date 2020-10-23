<template>
  <v-overlay opacity="1" color="grey lighten-4" absolute>
    <div class="account-management__loading" />
    <div v-if="!premiumVisible">
      <v-card class="account-management__card pb-6" width="500px" light>
        <div
          class="pt-6 pb-3 display-3 font-weight-black white--text account-management__card__title"
        >
          <span class="px-6">{{ $t('app.name') }}</span>
          <span class="d-block mb-3 pl-6 text-caption">
            {{ $t('app.moto') }}
          </span>
        </div>
        <connection-loading :connected="connected" />
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
      <privacy-notice />
      <div v-if="$interop.isPackaged" class="account-management__log-level">
        <log-level :value="loglevel" @input="changeLogLevel($event)" />
      </div>
    </div>

    <premium-reminder
      :display="displayPremium"
      @login-complete="loginComplete()"
      @upgrade="upgrade()"
    />
  </v-overlay>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import ConnectionLoading from '@/components/account-management/ConnectionLoading.vue';
import CreateAccount from '@/components/account-management/CreateAccount.vue';
import Login from '@/components/account-management/Login.vue';
import PremiumReminder from '@/components/account-management/PremiumReminder.vue';
import LogLevel from '@/components/helper/LogLevel.vue';
import PrivacyNotice from '@/components/PrivacyNotice.vue';
import { SyncConflict } from '@/store/session/types';
import { Message } from '@/store/types';
import { Credentials, UnlockPayload } from '@/typing/types';
import { CRITICAL, DEBUG, Level } from '@/utils/log-level';

@Component({
  components: {
    PrivacyNotice,
    ConnectionLoading,
    PremiumReminder,
    LogLevel,
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
  syncConflict!: SyncConflict;

  loglevel: Level = process.env.NODE_ENV === 'development' ? DEBUG : CRITICAL;

  premiumVisible = false;

  @Prop({ required: true, type: Boolean })
  logged!: boolean;

  get displayPremium(): boolean {
    return !this.premium && !this.message.title && this.premiumVisible;
  }

  @Emit()
  loginComplete() {
    this.dismiss();
  }

  async changeLogLevel(level: Level) {
    await this.$interop.restartBackend(level);
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
    this.accountCreation = false;
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
@import '~@/scss/scroll';

@keyframes scrollLarge {
  0% {
    transform: rotate(-13deg) translateY(0px);
  }

  100% {
    transform: rotate(-13deg) translateY(-600px);
  }
}

.account-management {
  &__card {
    z-index: 5;
    max-height: 90vh;
    overflow: auto;

    &__title {
      background-color: var(--v-primary-base);
    }

    @extend .themed-scrollbar;
  }

  &__loading {
    position: absolute;
    height: calc(100% + 1100px);
    width: calc(100% + 900px);
    left: -450px !important;
    top: -250px !important;
    opacity: 0.5;
    background: url(~@/assets/images/rotkipattern2.svg) repeat;
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
  }

  &__log-level {
    position: absolute !important;
    width: 56px !important;
    right: 12px !important;

    @media (min-width: 701px) {
      bottom: 12px !important;
    }

    @media (max-width: 700px) {
      top: 12px !important;
    }
  }
}

::v-deep {
  .v-overlay {
    &__content {
      display: flex;
      flex-direction: row;
      align-items: center;
      justify-content: center;
      height: 100%;
      width: 100%;
    }
  }
}
</style>
