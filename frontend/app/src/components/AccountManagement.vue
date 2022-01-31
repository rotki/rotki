<template>
  <v-overlay opacity="1" color="grey lighten-4">
    <div
      :class="{
        [$style.loading]: !xsOnly && !isTest
      }"
      data-cy="account-management__loading"
    />
    <div v-if="!premiumVisible">
      <v-card
        class="pb-4"
        :class="$style.card"
        :width="width"
        light
        data-cy="account-management"
      >
        <div
          class="pt-6 pb-3 text-h2 font-weight-black white--text"
          :class="$style.title"
        >
          <span class="px-6">{{ $t('app.name') }}</span>
          <span class="d-block mb-3 pl-6 text-caption">
            {{ $t('app.moto') }}
          </span>
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
      <privacy-notice />
      <div v-if="isPackaged" :class="$style.icon">
        <backend-settings-button />
      </div>
      <div v-if="!isPackaged" :class="$style.icon">
        <v-tooltip open-delay="400" top>
          <template #activator="{ on, attrs }">
            <v-btn
              icon
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

    watch(newUser, newUser => {
      if (newUser) {
        accountCreation.value = true;
      }
    });

    const { setConnected, connect } = store;

    const loginComplete = () => {
      dismissPremiumModal();
      emit('login-complete');
    };

    const { currentBreakpoint } = setupThemeCheck();
    const xsOnly = computed(() => currentBreakpoint.value.xsOnly);
    const width = computed(() => (xsOnly.value ? '100%' : '500px'));
    const premium = getPremium();

    const displayPremium = computed(
      () => !premium.value && !message.value.title && premiumVisible.value
    );

    const showPremiumDialog = () => {
      if (premium.value) {
        loginComplete();
        return;
      }
      premiumVisible.value = true;
    };

    const { syncConflict, login, createAccount } = setupSession();
    const interop = useInterop();

    const upgrade = () => {
      interop.navigateToPremium();
      loginComplete();
    };

    const showGetPremiumButton = () => {
      interop.premiumUserLoggedIn(premium.value);
    };

    const { restartBackend } = setupBackendManagement();

    onMounted(async () => {
      const { sessionOnly } = getBackendUrl();
      if (sessionOnly) {
        deleteBackendUrl();
        await restartBackend();
      }

      autolog.value = true;
      await login({ username: '', password: '' });
      if (logged.value) {
        showPremiumDialog();
        showGetPremiumButton();
      }
      autolog.value = false;
      if (newUser.value) {
        accountCreation.value = true;
      }
    });

    const setupBackend = async () => {
      if (connected.value) {
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
      loading.value = true;
      accountCreationError.value = '';
      const { message, success } = await createAccount(payload);
      loading.value = false;

      if (success) {
        accountCreation.value = false;

        if (logged.value) {
          showGetPremiumButton();
          loginComplete();
        }
      } else {
        accountCreationError.value =
          message ?? i18n.t('account_management.creation.error').toString();
      }
    };

    const userLogin = async (credentials: LoginCredentials) => {
      const { username, password, syncApproval } = credentials;
      loading.value = true;
      const { message } = await login({
        username,
        password,
        syncApproval
      });

      if (message) {
        errors.value = [message];
      }
      loading.value = false;
      if (logged.value) {
        setLastLogin(username);
        showPremiumDialog();
        showGetPremiumButton();
      }
    };

    const dismissPremiumModal = () => {
      premiumVisible.value = false;
    };

    return {
      xsOnly,
      width,
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
      isTest: !!process.env.VUE_APP_TEST,
      isPackaged: computed(() => interop.isPackaged),
      backendChanged,
      dismissPremiumModal,
      upgrade,
      userLogin,
      loginComplete,
      createNewAccount
    };
  }
});
</script>

<style module lang="scss">
@import '~@/scss/scroll';

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

.title {
  background-color: var(--v-primary-base);
}

.card {
  z-index: 5;
  max-height: 90vh;
  overflow: auto;

  @extend .themed-scrollbar;
}

.icon {
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
