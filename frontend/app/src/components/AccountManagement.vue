<template>
  <v-overlay :dark="false" opacity="1" color="grey lighten-4">
    <div
      class="animate"
      :class="{
        [$style.loading]: !xsOnly && !isTest,
        [$style['loading--paused']]: !animationEnabled
      }"
      data-cy="account-management__loading"
    />
    <div v-if="!premiumVisible" :class="$style.wrapper">
      <div />
      <v-card
        class="pb-4"
        :class="$style.card"
        light
        data-cy="account-management"
      >
        <div class="pa-6 text-h2 font-weight-black white--text primary">
          <div>{{ $t('app.name') }}</div>
          <div class="text-caption">
            {{ $t('app.moto') }}
          </div>
        </div>
        <connection-loading
          v-if="!connectionFailure"
          :connected="connected && !autolog"
        />
        <connection-failure v-else />
        <v-slide-y-transition>
          <login
            :loading="loading"
            :displayed="!accountCreation && connected"
            :sync-conflict="syncConflict"
            :errors="errors"
            @touched="errors = []"
            @login="userLogin($event)"
            @backend-changed="backendChanged($event)"
            @new-account="accountCreation = true"
          />
        </v-slide-y-transition>
        <v-slide-y-transition>
          <create-account
            :loading="loading"
            :displayed="accountCreation && connected"
            :error="accountCreationError"
            @error:clear="accountCreationError = ''"
            @cancel="accountCreation = false"
            @confirm="createNewAccount($event)"
          />
        </v-slide-y-transition>
      </v-card>
      <div :class="`${$style.icon} ${$style['icon--left']}`">
        <v-tooltip open-delay="400" top>
          <template #activator="{ on, attrs }">
            <v-btn
              text
              fab
              depressed
              color="primary"
              v-bind="attrs"
              v-on="on"
              @click="toggleAnimationEnabled"
            >
              <v-icon v-if="animationEnabled">mdi-pause</v-icon>
              <v-icon v-else>mdi-play</v-icon>
            </v-btn>
          </template>
          <span v-if="animationEnabled">
            {{ $t('frontend_settings.animations.disable') }} ({{
              $t('frontend_settings.animations.disable_hint')
            }})
          </span>
          <span v-else>{{ $t('frontend_settings.animations.enable') }}</span>
        </v-tooltip>
      </div>
      <privacy-notice />
      <div :class="`${$style.icon} ${$style['icon--right']}`">
        <template v-if="isPackaged">
          <backend-settings-button />
        </template>
        <template v-else>
          <v-tooltip open-delay="400" top>
            <template #activator="{ on, attrs }">
              <v-btn
                text
                fab
                depressed
                color="primary"
                v-bind="attrs"
                @click="$emit('about')"
                v-on="on"
              >
                <v-icon>mdi-information</v-icon>
              </v-btn>
            </template>
            <span>{{ $t('account_management.about_tooltip') }}</span>
          </v-tooltip>
        </template>
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
import {
  computed,
  defineComponent,
  onMounted,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set, useLocalStorage } from '@vueuse/core';
import ConnectionFailure from '@/components/account-management/ConnectionFailure.vue';
import ConnectionLoading from '@/components/account-management/ConnectionLoading.vue';
import CreateAccount from '@/components/account-management/CreateAccount.vue';
import Login from '@/components/account-management/Login.vue';
import PremiumReminder from '@/components/account-management/PremiumReminder.vue';
import {
  deleteBackendUrl,
  getBackendUrl,
  setLastLogin
} from '@/components/account-management/utils';
import BackendSettingsButton from '@/components/helper/BackendSettingsButton.vue';
import PrivacyNotice from '@/components/PrivacyNotice.vue';
import { setupBackendManagement } from '@/composables/backend';
import { setupThemeCheck } from '@/composables/common';
import { getPremium, setupSession } from '@/composables/session';
import { useInterop } from '@/electron-interop';
import i18n from '@/i18n';
import { useMainStore } from '@/store/store';
import { CreateAccountPayload, LoginCredentials } from '@/types/login';

export default defineComponent({
  name: 'AccountManagement',
  components: {
    BackendSettingsButton,
    ConnectionFailure,
    PrivacyNotice,
    ConnectionLoading,
    PremiumReminder,
    Login,
    CreateAccount
  },
  props: {
    logged: {
      required: true,
      type: Boolean
    }
  },
  emits: ['about', 'login-complete'],
  setup(props, { emit }) {
    const { logged } = toRefs(props);
    const accountCreation = ref(false);
    const loading = ref(false);
    const autolog = ref(false);
    const errors = ref<string[]>([]);
    const accountCreationError = ref('');
    const premiumVisible = ref(false);

    const store = useMainStore();
    const { connectionFailure, newUser, message, connected, updateNeeded } =
      toRefs(store);

    const animationEnabled = useLocalStorage(
      'rotki.login_animation_enabled',
      true
    );

    const toggleAnimationEnabled = () => {
      set(animationEnabled, !get(animationEnabled));
    };

    watch(newUser, newUser => {
      if (newUser) {
        set(accountCreation, true);
      }
    });

    const { setConnected, connect } = store;

    const loginComplete = () => {
      dismissPremiumModal();
      emit('login-complete');
    };

    const { currentBreakpoint } = setupThemeCheck();
    const xsOnly = computed(() => get(currentBreakpoint).xsOnly);
    const premium = getPremium();

    const displayPremium = computed(
      () => !get(premium) && !get(message).title && get(premiumVisible)
    );

    const showPremiumDialog = () => {
      if (get(premium)) {
        loginComplete();
        return;
      }
      set(premiumVisible, true);
    };

    const { syncConflict, login, createAccount } = setupSession();
    const interop = useInterop();

    const upgrade = () => {
      interop.navigateToPremium();
      loginComplete();
    };

    const showGetPremiumButton = () => {
      interop.premiumUserLoggedIn(get(premium));
    };

    const { restartBackend } = setupBackendManagement();

    onMounted(async () => {
      const { sessionOnly } = getBackendUrl();
      if (sessionOnly) {
        deleteBackendUrl();
        await restartBackend();
      }

      set(autolog, true);
      await login({ username: '', password: '' });
      if (get(logged)) {
        showPremiumDialog();
        showGetPremiumButton();
      }
      set(autolog, false);
      if (get(newUser)) {
        set(accountCreation, true);
      }
    });

    const setupBackend = async () => {
      if (get(connected)) {
        return;
      }

      const { sessionOnly, url } = getBackendUrl();
      if (!!url && !sessionOnly) {
        await backendChanged(url);
      } else {
        await restartBackend();
      }
    };

    const backendChanged = async (url: string | null) => {
      setConnected(false);
      if (!url) {
        await restartBackend();
      }
      await connect(url);
    };

    setupBackend().then();

    const createNewAccount = async (payload: CreateAccountPayload) => {
      set(loading, true);
      set(accountCreationError, '');
      const result = await createAccount(payload);
      set(loading, false);

      if (result.success) {
        set(accountCreation, false);

        if (get(logged)) {
          showGetPremiumButton();
          loginComplete();
        }
      } else {
        set(
          accountCreationError,
          result.message ??
            i18n.t('account_management.creation.error').toString()
        );
      }
    };

    const userLogin = async (credentials: LoginCredentials) => {
      const { username, password, syncApproval } = credentials;
      set(loading, true);
      const result = await login({
        username,
        password,
        syncApproval
      });

      if (!result.success) {
        set(errors, [result.message]);
      }
      set(loading, false);
      if (get(logged)) {
        setLastLogin(username);
        showPremiumDialog();
        showGetPremiumButton();
      }
    };

    const dismissPremiumModal = () => {
      set(premiumVisible, false);
    };

    return {
      xsOnly,
      updateNeeded,
      autolog,
      connected,
      connectionFailure,
      loading,
      displayPremium,
      premiumVisible,
      accountCreation,
      accountCreationError,
      errors,
      syncConflict,
      isTest: !!import.meta.env.VITE_TEST,
      isPackaged: computed(() => interop.isPackaged),
      backendChanged,
      dismissPremiumModal,
      upgrade,
      userLogin,
      loginComplete,
      createNewAccount,
      animationEnabled,
      toggleAnimationEnabled
    };
  }
});
</script>

<style module lang="scss">
@keyframes scrollLarge {
  0% {
    transform: rotate(-13deg) translateY(0px);
  }

  100% {
    transform: rotate(-13deg) translateY(-600px);
  }
}

.loading {
  position: absolute;
  height: calc(100% + 1100px);
  width: calc(100% + 900px);
  left: -450px !important;
  top: -250px !important;
  opacity: 0.5;
  background: url(/assets/images/rotkipattern2.svg) repeat;
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

  &--paused {
    animation-play-state: paused;
  }
}

.wrapper {
  width: 600px;
  max-width: 100%;
  padding: 32px 16px 24px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100vh;

  @media (max-height: 800px) {
    padding-top: 0;
  }
}

.card {
  z-index: 5;
  max-height: calc(100vh - 140px);
  overflow: auto;
}

.icon {
  position: absolute !important;
  bottom: 12px;

  &--left {
    left: 12px;
  }

  &--right {
    right: 12px;
  }

  @media (max-width: 700px) {
    top: 12px;
    bottom: auto;
  }
}

:global {
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
