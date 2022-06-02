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

        <v-row no-gutters align="end">
          <v-col>
            <v-checkbox
              v-model="rememberUsername"
              :disabled="customBackendDisplay || rememberPassword"
              color="primary"
              hide-details
              class="mt-0 mb-2 remember"
              :label="$t('login.remember_username')"
            />
            <v-row no-gutters>
              <v-col cols="auto">
                <v-checkbox
                  v-if="$interop.isPackaged"
                  v-model="rememberPassword"
                  :disabled="customBackendDisplay"
                  color="primary"
                  hide-details
                  class="mt-0 pt-0 remember"
                  :label="$t('login.remember_password')"
                />
              </v-col>
              <v-col>
                <v-tooltip right max-width="200">
                  <template #activator="{ on }">
                    <v-icon small v-on="on"> mdi-help-circle </v-icon>
                  </template>
                  <div class="remember__tooltip">
                    {{ $t('login.remember_password_tooltip') }}
                  </div>
                </v-tooltip>
              </v-col>
            </v-row>
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
          <div class="animate mt-4">
            <v-divider />
            <v-row no-gutters class="mt-4" align="center">
              <v-col>
                <v-text-field
                  v-model="customBackendUrl"
                  outlined
                  prepend-inner-icon="mdi-server"
                  :rules="customBackendRules"
                  :disabled="customBackendSaved"
                  :label="$t('login.custom_backend.label')"
                  :placeholder="$t('login.custom_backend.placeholder')"
                  :hint="$t('login.custom_backend.hint')"
                  @keypress.enter="saveCustomBackend"
                />
              </v-col>
              <v-col cols="auto" class="pb-7">
                <v-btn
                  v-if="!customBackendSaved"
                  class="ml-4"
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
                  class="mt-0"
                  hide-details
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
            class="animate login__sync-error"
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
            class="animate mt-4 mb-0"
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
import { get, set, useLocalStorage } from '@vueuse/core';
import {
  deleteBackendUrl,
  getBackendUrl,
  saveBackendUrl
} from '@/components/account-management/utils';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { interop } from '@/electron-interop';
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

const KEY_REMEMBER_USERNAME = 'rotki.remember_username';
const KEY_REMEMBER_PASSWORD = 'rotki.remember_password';
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
    const rememberUsername: Ref<boolean> = ref(false);
    const rememberPassword: Ref<boolean> = ref(false);
    const customBackendDisplay: Ref<boolean> = ref(false);
    const customBackendUrl: Ref<string> = ref('');
    const customBackendSessionOnly: Ref<boolean> = ref(false);
    const customBackendSaved: Ref<boolean> = ref(false);
    const valid: Ref<boolean> = ref(false);

    const form: Ref<any> = ref(null);
    const usernameRef: Ref<any> = ref(null);
    const passwordRef: Ref<any> = ref(null);

    const savedRememberUsername = useLocalStorage(KEY_REMEMBER_USERNAME, null);
    const savedRememberPassword = useLocalStorage(KEY_REMEMBER_PASSWORD, null);
    const savedUsername = useLocalStorage(KEY_USERNAME, '');

    watch(username, () => {
      touched();
    });

    watch(password, () => {
      touched();
    });

    const isLoggedInError = computed<boolean>(() => {
      return !!(get(errors) as string[]).find(error =>
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
      return get(syncConflict).payload?.localLastModified ?? 0;
    });

    const remoteLastModified = computed<number>(() => {
      return get(syncConflict).payload?.remoteLastModified ?? 0;
    });

    const serverColor = computed<string | null>(() => {
      if (get(customBackendSessionOnly)) {
        return 'primary';
      } else if (get(customBackendSaved)) {
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
        focusElement(get(username) ? get(passwordRef) : get(usernameRef));
      });
    };

    const saveCustomBackend = () => {
      saveBackendUrl({
        url: get(customBackendUrl),
        sessionOnly: get(customBackendSessionOnly)
      });
      backendChanged(get(customBackendUrl));
      set(customBackendSaved, true);
      set(customBackendDisplay, false);
    };

    const clearCustomBackend = () => {
      set(customBackendUrl, '');
      set(customBackendSessionOnly, false);
      deleteBackendUrl();
      backendChanged(null);
      set(customBackendSaved, false);
      set(customBackendDisplay, false);
    };

    const checkRememberUsername = () => {
      set(
        rememberUsername,
        !!get(savedRememberUsername) || !!get(savedRememberPassword)
      );
    };

    const loadSettings = async () => {
      set(rememberPassword, !!get(savedRememberPassword));
      checkRememberUsername();
      set(username, get(savedUsername));
      const { sessionOnly, url } = getBackendUrl();
      set(customBackendUrl, url);
      set(customBackendSessionOnly, sessionOnly);
      set(customBackendSaved, !!url);

      if (interop.isPackaged && get(rememberPassword) && get(username)) {
        const savedPassword = await interop.getPassword(get(username));

        if (savedPassword) {
          set(password, savedPassword);
          login();
        }
      }
    };

    onMounted(() => {
      loadSettings();
      updateFocus();
    });

    watch(displayed, () => {
      set(username, '');
      set(password, '');

      get(form)?.reset();

      loadSettings();
      updateFocus();
    });

    watch(rememberUsername, (remember: boolean, previous: boolean) => {
      if (remember === previous) {
        return;
      }

      if (!remember) {
        set(savedRememberUsername, null);
        set(savedUsername, null);
      } else {
        set(savedRememberUsername, 'true');
      }
    });

    watch(rememberPassword, (remember: boolean, previous: boolean) => {
      if (remember === previous) {
        return;
      }

      if (!remember) {
        set(savedRememberPassword, null);
        if (interop.isPackaged) {
          interop.clearPassword();
        }
      } else {
        set(savedRememberPassword, 'true');
      }

      checkRememberUsername();
    });

    const login = (syncApproval: SyncApproval = 'unknown') => {
      const credentials: LoginCredentials = {
        username: get(username),
        password: get(password),
        syncApproval
      };
      emit('login', credentials);
      if (get(rememberUsername)) {
        set(savedUsername, get(username));
      }

      if (get(rememberPassword) && interop.isPackaged) {
        interop.storePassword(get(username), get(password));
      }
    };

    return {
      logoutRemoteSession,
      customBackendRules,
      usernameRules,
      passwordRules,
      username,
      password,
      rememberUsername,
      rememberPassword,
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

.remember {
  width: 190px;

  &__tooltip {
    font-size: 0.8rem;
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
