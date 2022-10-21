<template>
  <v-slide-y-transition>
    <div class="login">
      <v-card-title>
        {{ tc('login.title') }}
      </v-card-title>
      <v-card-text class="pb-2">
        <v-form ref="form" v-model="valid">
          <v-text-field
            ref="usernameRef"
            v-model="username"
            class="login__fields__username"
            color="secondary"
            outlined
            single-line
            :label="tc('login.label_username')"
            prepend-inner-icon="mdi-account"
            :rules="usernameRules"
            :disabled="
              loading || !!syncConflict.message || customBackendDisplay
            "
            required
            @keypress.enter="login()"
          />

          <revealable-input
            ref="passwordRef"
            v-model="password"
            outlined
            :rules="passwordRules"
            :disabled="
              loading || !!syncConflict.message || customBackendDisplay
            "
            type="password"
            required
            class="login__fields__password"
            color="secondary"
            :label="tc('login.label_password')"
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
                class="mt-2 remember"
                :label="tc('login.remember_username')"
              />
              <v-row v-if="isPackaged" class="pt-2" no-gutters>
                <v-col cols="auto">
                  <v-checkbox
                    v-model="rememberPassword"
                    :disabled="customBackendDisplay"
                    color="primary"
                    hide-details
                    class="mt-0 pt-0 remember"
                    :label="tc('login.remember_password')"
                  />
                </v-col>
                <v-col>
                  <v-tooltip right max-width="200">
                    <template #activator="{ on }">
                      <v-icon small v-on="on"> mdi-help-circle </v-icon>
                    </template>
                    <div class="remember__tooltip">
                      {{ tc('login.remember_password_tooltip') }}
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
                <span v-text="tc('login.custom_backend.tooltip')" />
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
                    :label="tc('login.custom_backend.label')"
                    :placeholder="tc('login.custom_backend.placeholder')"
                    :hint="tc('login.custom_backend.hint')"
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
                    :label="tc('login.custom_backend.session_only')"
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
                {{ tc('login.sync_error.title') }}
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
                <div class="mt-2">{{ tc('login.sync_error.question') }}</div>
              </div>

              <v-row no-gutters justify="end" class="mt-2">
                <v-col cols="3" class="shrink">
                  <v-btn color="error" depressed @click="login('no')">
                    {{ tc('common.actions.no') }}
                  </v-btn>
                </v-col>
                <v-col cols="3" class="shrink">
                  <v-btn color="success" depressed @click="login('yes')">
                    {{ tc('common.actions.yes') }}
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
                    {{ tc('login.logout') }}
                  </v-btn>
                </v-col>
              </v-row>
            </v-alert>
          </transition>
        </v-form>
      </v-card-text>
      <v-card-actions class="login__actions d-block">
        <v-alert v-if="showUpgradeMessage" type="warning" text>
          {{ tc('login.upgrading_db_warning') }}
        </v-alert>
        <span>
          <v-btn
            class="login__button__sign-in"
            depressed
            color="primary"
            :disabled="
              !valid ||
              loading ||
              !!syncConflict.message ||
              customBackendDisplay
            "
            :loading="loading"
            @click="login()"
          >
            {{ tc('login.button_signin') }}
          </v-btn>
        </span>
        <v-divider class="my-4" />
        <span class="login__actions__footer">
          <a
            data-cy="new-account"
            class="login__button__new-account font-weight-bold secondary--text"
            @click="newAccount()"
          >
            {{ tc('login.button_new_account') }}
          </a>
        </span>
      </v-card-actions>
    </div>
  </v-slide-y-transition>
</template>
<script setup lang="ts">
import { PropType, Ref } from 'vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { useInterop } from '@/electron-interop';
import { useSessionStore } from '@/store/session';
import { SyncConflict } from '@/store/session/types';
import { LoginCredentials, SyncApproval } from '@/types/login';
import {
  deleteBackendUrl,
  getBackendUrl,
  saveBackendUrl
} from '@/utils/account-management';

const KEY_REMEMBER_USERNAME = 'rotki.remember_username';
const KEY_REMEMBER_PASSWORD = 'rotki.remember_password';
const KEY_USERNAME = 'rotki.username';

const props = defineProps({
  loading: { required: true, type: Boolean },
  syncConflict: { required: true, type: Object as PropType<SyncConflict> },
  errors: { required: false, type: Array, default: () => [] },
  showUpgradeMessage: { required: false, type: Boolean, default: false }
});

const emit = defineEmits([
  'backend-changed',
  'login',
  'new-account',
  'touched'
]);

const { syncConflict, errors } = toRefs(props);

const touched = () => emit('touched');
const newAccount = () => emit('new-account');
const backendChanged = (url: string | null) => emit('backend-changed', url);

const { logoutRemoteSession } = useSessionStore();

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

const { tc } = useI18n();

const customBackendRules = [
  (v: string) => !!v || tc('login.custom_backend.validation.non_empty'),
  (v: string) =>
    (v &&
      v.length < 300 &&
      /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}(\.[a-zA-Z0-9()]{1,6})?\b([-a-zA-Z0-9()@:%_+.~#?&/=]*)$/.test(
        v
      )) ||
    tc('login.custom_backend.validation.url')
];

const usernameRules = [
  (v: string) => !!v || tc('login.validation.non_empty_username'),
  (v: string) =>
    (v && /^[0-9a-zA-Z_.-]+$/.test(v)) || tc('login.validation.valid_username')
];

const passwordRules = [
  (v: string) => !!v || tc('login.validation.non_empty_password')
];

const { clearPassword, getPassword, isPackaged, storePassword } = useInterop();

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

  if (isPackaged && get(rememberPassword) && get(username)) {
    const savedPassword = await getPassword(get(username));

    if (savedPassword) {
      set(password, savedPassword);
      await login();
    }
  }
};

onMounted(async () => {
  await loadSettings();
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

watch(rememberPassword, async (remember: boolean, previous: boolean) => {
  if (remember === previous) {
    return;
  }

  if (!remember) {
    set(savedRememberPassword, null);
    if (isPackaged) {
      await clearPassword();
    }
  } else {
    set(savedRememberPassword, 'true');
  }

  checkRememberUsername();
});

const login = async (syncApproval: SyncApproval = 'unknown') => {
  const credentials: LoginCredentials = {
    username: get(username),
    password: get(password),
    syncApproval
  };
  emit('login', credentials);
  if (get(rememberUsername)) {
    set(savedUsername, get(username));
  }

  if (get(rememberPassword) && isPackaged) {
    await storePassword(get(username), get(password));
  }
};
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
