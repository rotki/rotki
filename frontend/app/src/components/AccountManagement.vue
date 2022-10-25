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
          <div>{{ t('app.name') }}</div>
          <div class="text-caption">
            {{ t('app.moto') }}
          </div>
        </div>
        <connection-loading
          v-if="!hasConnectionFailed"
          :connected="connected && !autolog"
        />
        <connection-failure v-else />
        <div v-if="connected" data-cy="account-management-forms">
          <login-form
            v-if="!accountCreation"
            :loading="loading"
            :sync-conflict="syncConflict"
            :errors="errors"
            :show-upgrade-message="showUpgradeMessage"
            @touched="errors = []"
            @login="userLogin($event)"
            @backend-changed="backendChanged($event)"
            @new-account="accountCreation = true"
          />
          <create-account-form
            v-else
            :loading="loading"
            :error="accountCreationError"
            @error:clear="accountCreationError = ''"
            @cancel="accountCreation = false"
            @confirm="createNewAccount($event)"
          />
        </div>
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
            {{ t('frontend_settings.animations.disable') }} ({{
              t('frontend_settings.animations.disable_hint')
            }})
          </span>
          <span v-else>{{ t('frontend_settings.animations.enable') }}</span>
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
            <span>{{ t('account_management.about_tooltip') }}</span>
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

<script setup lang="ts">
import ConnectionFailure from '@/components/account-management/ConnectionFailure.vue';
import ConnectionLoading from '@/components/account-management/ConnectionLoading.vue';
import BackendSettingsButton from '@/components/helper/OnboardingSettingsButton.vue';
import PrivacyNotice from '@/components/PrivacyNotice.vue';
import { useBackendManagement } from '@/composables/backend';
import { useTheme } from '@/composables/common';
import { usePremium } from '@/composables/premium';
import { useInterop } from '@/electron-interop';
import { useMainStore } from '@/store/main';
import { useMessageStore } from '@/store/message';
import { useSessionStore } from '@/store/session';
import { CreateAccountPayload, LoginCredentials } from '@/types/login';
import { startPromise } from '@/utils';
import {
  deleteBackendUrl,
  getBackendUrl,
  setLastLogin
} from '@/utils/account-management';

const LoginForm = defineAsyncComponent(
  () => import('@/components/account-management/LoginForm.vue')
);
const CreateAccountForm = defineAsyncComponent(
  () => import('@/components/account-management/CreateAccountForm.vue')
);

const props = defineProps({
  logged: {
    required: true,
    type: Boolean
  }
});

const emit = defineEmits<{
  (e: 'about'): void;
  (e: 'login-complete'): void;
}>();

const { t } = useI18n();
const { logged } = toRefs(props);
const accountCreation = ref(false);
const loading = ref(false);
const showUpgradeMessage = ref(false);
const autolog = ref(false);
const errors = ref<string[]>([]);
const accountCreationError = ref('');
const premiumVisible = ref(false);

const store = useMainStore();
const {
  connectionFailure: hasConnectionFailed,
  newUser,
  connected
} = toRefs(store);

const { message } = storeToRefs(useMessageStore());

const animationEnabled = useLocalStorage('rotki.login_animation_enabled', true);

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

const { currentBreakpoint } = useTheme();
const xsOnly = computed(() => get(currentBreakpoint).xsOnly);
const premium = usePremium();

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

const sessionStore = useSessionStore();
const { login, createAccount } = sessionStore;
const { syncConflict } = storeToRefs(sessionStore);
const interop = useInterop();

const upgrade = () => {
  interop.navigateToPremium();
  loginComplete();
};

const showGetPremiumButton = () => {
  interop.premiumUserLoggedIn(get(premium));
};

const { restartBackend } = useBackendManagement();

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

startPromise(setupBackend());

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
      result.message ?? t('account_management.creation.error').toString()
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

const { isPackaged } = useInterop();

const isTest = !!import.meta.env.VITE_TEST;

const { start, stop } = useTimeoutFn(
  () => {
    set(showUpgradeMessage, true);
  },
  15000,
  {
    immediate: false
  }
);

watch(loading, loading => {
  if (loading) {
    start();
  } else {
    stop();
    set(showUpgradeMessage, false);
  }
});

defineExpose({
  userLogin,
  createNewAccount
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
