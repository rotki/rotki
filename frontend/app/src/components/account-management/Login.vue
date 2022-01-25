<template>
  <div v-if="displayed" class="login">
    <v-card-title>
      {{ $t('login.title') }}
    </v-card-title>
    <v-card-text>
      <v-form ref="form" v-model="valid">
        <v-text-field
          ref="usernameRef"
          v-model="username"
          class="login__fields__username"
          color="secondary"
          outlined
          single-line
          :label="$t('login.label_username')"
          prepend-inner-icon="mdi-account"
          :rules="usernameRules"
          :disabled="loading || !!syncConflict.message || customBackendDisplay"
          required
          @keypress.enter="login()"
        />

        <revealable-input
          ref="passwordRef"
          v-model="password"
          outlined
          :rules="passwordRules"
          :disabled="loading || !!syncConflict.message || customBackendDisplay"
          type="password"
          required
          class="login__fields__password"
          color="secondary"
          :label="$t('login.label_password')"
          prepend-icon="mdi-lock"
          @keypress.enter="login()"
        />

        <v-row no-gutters align="center">
          <v-col>
            <v-checkbox
              v-model="rememberUser"
              :disabled="customBackendDisplay"
              color="primary"
              hide-details
              class="mt-0"
              :label="$t('login.remember_me')"
            />
          </v-col>
          <v-col cols="auto">
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <v-btn
                  icon
                  :color="serverColor"
                  v-bind="attrs"
                  v-on="on"
                  @click="customBackendDisplay = !customBackendDisplay"
                >
                  <v-icon>mdi-server</v-icon>
                </v-btn>
              </template>
              <span v-text="$t('login.custom_backend.tooltip')" />
            </v-tooltip>
          </v-col>
        </v-row>

        <transition v-if="customBackendDisplay" name="bounce">
          <div>
            <v-divider />
            <v-row no-gutters class="mt-4" align="center">
              <v-col>
                <v-text-field
                  v-model="customBackendUrl"
                  prepend-icon="mdi-server"
                  :rules="customBackendRules"
                  :disabled="customBackendSaved"
                  :label="$t('login.custom_backend.label')"
                  :placeholder="$t('login.custom_backend.placeholder')"
                  :hint="$t('login.custom_backend.hint')"
                  @keypress.enter="saveCustomBackend"
                />
              </v-col>
              <v-col cols="auto">
                <v-btn
                  v-if="!customBackendSaved"
                  class="ms-2"
                  icon
                  @click="saveCustomBackend()"
                >
                  <v-icon>mdi-content-save</v-icon>
                </v-btn>
                <v-btn v-else icon @click="clearCustomBackend()">
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
              </v-col>
            </v-row>
            <v-row no-gutters>
              <v-col>
                <v-checkbox
                  v-model="customBackendSessionOnly"
                  :disabled="customBackendSaved"
                  :label="$t('login.custom_backend.session_only')"
                />
              </v-col>
            </v-row>
          </div>
        </transition>

        <transition name="bounce">
          <v-alert
            v-if="!!syncConflict.message"
            class="login__sync-error"
            text
            prominent
            outlined
            type="info"
            icon="mdi-cloud-download"
          >
            <div class="login__sync-error__header text-h6">
              {{ $t('login.sync_error.title') }}
            </div>
            <div class="login__sync-error__body mt-2">
              <div>
                <div>{{ syncConflict.message }}</div>
                <ul class="mt-2">
                  <li>
                    <i18n path="login.sync_error.local_modified">
                      <div class="font-weight-medium">
                        <date-display :timestamp="localLastModified" />
                      </div>
                    </i18n>
                  </li>
                  <li class="mt-2">
                    <i18n path="login.sync_error.remote_modified">
                      <div class="font-weight-medium">
                        <date-display :timestamp="remoteLastModified" />
                      </div>
                    </i18n>
                  </li>
                  <li class="mt-2">
                    <i18n path="login.sync_error.local_size">
                      <div class="font-weight-medium">
                        {{ localSize }}
                      </div>
                    </i18n>
                  </li>
                  <li class="mt-2">
                    <i18n path="login.sync_error.remote_size">
                      <div class="font-weight-medium">
                        {{ remoteSize }}
                      </div>
                    </i18n>
                  </li>
                </ul>
              </div>
              <div class="mt-2">{{ $t('login.sync_error.question') }}</div>
            </div>

            <v-row no-gutters justify="end" class="mt-2">
              <v-col cols="3" class="shrink">
                <v-btn color="error" depressed @click="login('no')">
                  {{ $t('login.sync_error.button_no') }}
                </v-btn>
              </v-col>
              <v-col cols="3" class="shrink">
                <v-btn color="success" depressed @click="login('yes')">
                  {{ $t('login.sync_error.button_yes') }}
                </v-btn>
              </v-col>
            </v-row>
          </v-alert>
        </transition>
        <transition name="bounce">
          <v-alert
            v-if="errors.length > 0"
            text
            outlined
            type="error"
            icon="mdi-alert-circle-outline"
          >
            <v-row>
              <v-col class="grow">
                <span v-for="(error, i) in errors" :key="i" v-text="error" />
              </v-col>
              <v-col class="shrink">
                <v-btn
                  v-if="isLoggedInError"
                  depressed
                  color="primary"
                  @click="logout"
                >
                  {{ $t('login.logout') }}
                </v-btn>
              </v-col>
            </v-row>
          </v-alert>
        </transition>
      </v-form>
    </v-card-text>
    <v-card-actions class="login__actions d-block">
      <span>
        <v-btn
          class="login__button__sign-in"
          depressed
          color="primary"
          :disabled="
            !valid || loading || !!syncConflict.message || customBackendDisplay
          "
          :loading="loading"
          @click="login()"
        >
          {{ $t('login.button_signin') }}
        </v-btn>
      </span>
      <v-divider class="my-4" />
      <span class="login__actions__footer">
        <a
          class="login__button__new-account font-weight-bold secondary--text"
          @click="newAccount()"
        >
          {{ $t('login.button_new_account') }}
        </a>
      </span>
    </v-card-actions>
  </div>
</template>
<script lang="ts">
import {
  computed,
  defineComponent,
  nextTick,
  onMounted,
  PropType,
  ref,
  Ref,
  toRefs,
  watch
} from '@vue/composition-api';
import {
  deleteBackendUrl,
  getBackendUrl,
  saveBackendUrl
} from '@/components/account-management/utils';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import i18n from '@/i18n';
import { SyncConflict } from '@/store/session/types';
import { useStore } from '@/store/utils';
import { LoginCredentials, SyncApproval } from '@/types/login';

const setupLogout = () => {
  const store = useStore();
  const logoutRemoteSession = () => store.dispatch('logoutRemoteSession');

  return {
    logoutRemoteSession
  };
};

const KEY_REMEMBER = 'rotki.remember';
const KEY_USERNAME = 'rotki.username';

const customBackendRules = [
  (v: string) =>
    !!v || i18n.t('login.custom_backend.validation.non_empty').toString(),
  (v: string) =>
    (v &&
      v.length < 300 &&
      /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}(\.[a-zA-Z0-9()]{1,6})?\b([-a-zA-Z0-9()@:%_+.~#?&/=]*)$/.test(
        v
      )) ||
    i18n.t('login.custom_backend.validation.url').toString()
];

const usernameRules = [
  (v: string) => !!v || i18n.t('login.validation.non_empty_username'),
  (v: string) =>
    (v && /^[0-9a-zA-Z_.-]+$/.test(v)) ||
    i18n.t('login.validation.valid_username').toString()
];

const passwordRules = [
  (v: string) => !!v || i18n.t('login.validation.non_empty_password').toString()
];

export default defineComponent({
  name: 'Login',
  components: { RevealableInput },
  props: {
    displayed: { required: true, type: Boolean },
    loading: { required: true, type: Boolean },
    syncConflict: { required: true, type: Object as PropType<SyncConflict> },
    errors: { required: false, type: Array, default: () => [] }
  },
  emits: ['backend-changed', 'login', 'new-account', 'touched'],
  setup(props, { emit }) {
    const { displayed, syncConflict, errors } = toRefs(props);

    const touched = () => emit('touched');
    const newAccount = () => emit('new-account');
    const backendChanged = (url: string | null) => emit('backend-changed', url);

    const { logoutRemoteSession } = setupLogout();

    const username: Ref<string> = ref('');
    const password: Ref<string> = ref('');
    const rememberUser: Ref<boolean> = ref(false);
    const customBackendDisplay: Ref<boolean> = ref(false);
    const customBackendUrl: Ref<string> = ref('');
    const customBackendSessionOnly: Ref<boolean> = ref(false);
    const customBackendSaved: Ref<boolean> = ref(false);
    const valid: Ref<boolean> = ref(false);

    const form: Ref<any> = ref(null);
    const usernameRef: Ref<any> = ref(null);
    const passwordRef: Ref<any> = ref(null);

    watch(username, () => {
      touched();
    });

    watch(password, () => {
      touched();
    });

    const isLoggedInError = computed<boolean>(() => {
      return !!(errors.value as string[]).find(error =>
        error.includes('is already logged in')
      );
    });

    const logout = async () => {
      const { success } = await logoutRemoteSession();
      if (success) {
        touched();
      }
    };

    const localLastModified = computed<number>(() => {
      return syncConflict.value.payload?.localLastModified ?? 0;
    });

    const remoteLastModified = computed<number>(() => {
      return syncConflict.value.payload?.remoteLastModified ?? 0;
    });

    const localSize = computed<string>(() => {
      return syncConflict.value.payload?.localSize ?? '';
    });

    const remoteSize = computed<string>(() => {
      return syncConflict.value.payload?.remoteSize ?? '';
    });

    const serverColor = computed<string | null>(() => {
      if (customBackendSessionOnly.value) {
        return 'primary';
      } else if (customBackendSaved.value) {
        return 'success';
      }

      return null;
    });

    const focusElement = (element: any) => {
      if (element) {
        const input = element.$el.querySelector(
          'input:not([type=hidden])'
        ) as HTMLInputElement;
        input.focus();
      }
    };

    const updateFocus = () => {
      nextTick(() => {
        focusElement(username.value ? passwordRef.value : usernameRef.value);
      });
    };

    const saveCustomBackend = () => {
      saveBackendUrl({
        url: customBackendUrl.value,
        sessionOnly: customBackendSessionOnly.value
      });
      backendChanged(customBackendUrl.value);
      customBackendSaved.value = true;
      customBackendDisplay.value = false;
    };

    const clearCustomBackend = () => {
      customBackendUrl.value = '';
      customBackendSessionOnly.value = false;
      deleteBackendUrl();
      backendChanged(null);
      customBackendSaved.value = false;
      customBackendDisplay.value = false;
    };

    const loadSettings = () => {
      rememberUser.value = !!localStorage.getItem(KEY_REMEMBER);
      username.value = localStorage.getItem(KEY_USERNAME) ?? '';
      const { sessionOnly, url } = getBackendUrl();
      customBackendUrl.value = url;
      customBackendSessionOnly.value = sessionOnly;
      customBackendSaved.value = !!url;
    };

    onMounted(() => {
      loadSettings();
      updateFocus();
    });

    watch(displayed, () => {
      username.value = '';
      password.value = '';

      form.value?.reset();

      loadSettings();
      updateFocus();
    });

    watch(rememberUser, (remember: boolean, previous: boolean) => {
      if (remember === previous) {
        return;
      }

      if (!remember) {
        localStorage.removeItem(KEY_REMEMBER);
        localStorage.removeItem(KEY_USERNAME);
      } else {
        localStorage.setItem(KEY_REMEMBER, `${true}`);
      }
    });

    const login = (syncApproval: SyncApproval = 'unknown') => {
      const credentials: LoginCredentials = {
        username: username.value,
        password: password.value,
        syncApproval
      };
      emit('login', credentials);
      if (rememberUser.value) {
        localStorage.setItem(KEY_USERNAME, username.value);
      }
    };

    return {
      logoutRemoteSession,
      customBackendRules,
      usernameRules,
      passwordRules,
      username,
      password,
      rememberUser,
      customBackendDisplay,
      customBackendUrl,
      customBackendSessionOnly,
      customBackendSaved,
      valid,
      form,
      passwordRef,
      usernameRef,
      newAccount,
      login,
      logout,
      isLoggedInError,
      localLastModified,
      remoteLastModified,
      localSize,
      remoteSize,
      serverColor,
      saveCustomBackend,
      clearCustomBackend
    };
  }
});
</script>

<style scoped lang="scss">
.login {
  &__actions {
    padding: 16px !important;

    &__footer {
      font-size: 0.9em;
    }

    span,
    button {
      display: block;
      width: 100%;
      text-align: center;
    }
  }

  &__sync-error {
    &__body {
      margin-top: 5px;
      margin-bottom: 8px;
    }
  }
}

.bounce-enter-active {
  animation: bounce-in 0.5s;
}

.bounce-leave-active {
  animation: bounce-in 0.5s reverse;
}

@keyframes bounce-in {
  0% {
    transform: scale(0);
  }

  50% {
    transform: scale(1.1);
  }

  100% {
    transform: scale(1);
  }
}
</style>
