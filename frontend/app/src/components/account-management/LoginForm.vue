<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { type LoginCredentials, type SyncApproval } from '@/types/login';

const props = withDefaults(
  defineProps<{
    loading: boolean;
    errors?: string[];
  }>(),
  {
    errors: () => []
  }
);

const emit = defineEmits<{
  (e: 'touched'): void;
  (e: 'new-account'): void;
  (e: 'login', credentials: LoginCredentials): void;
  (e: 'backend-changed', url: string | null): void;
}>();

const { t } = useI18n();

const { errors } = toRefs(props);

const authStore = useSessionAuthStore();
const { conflictExist } = storeToRefs(authStore);
const { resetSyncConflict, resetIncompleteUpgradeConflict } = authStore;

const touched = () => emit('touched');
const newAccount = () => emit('new-account');
const backendChanged = (url: string | null) => emit('backend-changed', url);

const { logoutRemoteSession } = useSessionStore();
const { usageGuideUrl } = useInterop();
const css = useCssModule();

const username: Ref<string> = ref('');
const password: Ref<string> = ref('');
const rememberUsername: Ref<boolean> = ref(false);
const rememberPassword: Ref<boolean> = ref(false);
const customBackendDisplay: Ref<boolean> = ref(false);
const customBackendUrl: Ref<string> = ref('');
const customBackendSessionOnly: Ref<boolean> = ref(false);
const customBackendSaved: Ref<boolean> = ref(false);

const usernameRef: Ref = ref();
const passwordRef: Ref = ref();

const savedRememberUsername = useLocalStorage('rotki.remember_username', null);
const savedRememberPassword = useLocalStorage('rotki.remember_password', null);
const savedUsername = useLocalStorage('rotki.username', '');

const rules = {
  username: {
    required: helpers.withMessage(
      t('login.validation.non_empty_username'),
      required
    ),
    isValidUsername: helpers.withMessage(
      t('login.validation.valid_username'),
      (v: string): boolean => !!(v && /^[\w.-]+$/.test(v))
    )
  },
  password: {
    required: helpers.withMessage(
      t('login.validation.non_empty_password'),
      required
    )
  },
  customBackendUrl: {
    required: helpers.withMessage(
      t('login.custom_backend.validation.non_empty'),
      requiredIf(customBackendDisplay)
    ),
    isValidUrl: helpers.withMessage(
      t('login.custom_backend.validation.url'),
      (v: string): boolean =>
        !get(customBackendDisplay) ||
        (v.length < 300 &&
          /^https?:\/\/(www\.)?[\w#%+.:=@~-]{1,256}(\.[\d()A-Za-z]{1,6})?\b([\w#%&()+./:=?@~-]*)$/.test(
            v
          ))
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    username,
    password,
    customBackendUrl
  },
  {
    $autoDirty: true
  }
);

const { clearPassword, getPassword, isPackaged, storePassword } = useInterop();

watch(
  [username, password],
  ([username, password], [oldUsername, oldPassword]) => {
    // touched should not be emitted when restoring from local storage
    if (!oldUsername && username === get(savedUsername)) {
      return;
    }
    if (username !== oldUsername || password !== oldPassword) {
      touched();
    }
  }
);

const isLoggedInError = useArraySome(errors, error =>
  error.includes('is already logged in')
);

const usernameError = useArrayFind(errors, error => error.startsWith('User '));
const passwordError = useArrayFind(errors, error =>
  error.startsWith('Wrong password ')
);

const hasServerError = computed(
  () => !!get(usernameError) || !!get(passwordError)
);

const usernameErrors = computed(() => {
  const formErrors = [...get(v$).username.$errors.map(e => e.$message)];
  const serverError = get(usernameError);
  if (serverError) {
    formErrors.push(serverError);
  }

  return formErrors;
});

const passwordErrors = computed(() => {
  const formErrors = [...get(v$).password.$errors.map(e => e.$message)];
  const serverError = get(passwordError);
  if (serverError) {
    formErrors.push(serverError);
  }

  return formErrors;
});

const logout = async () => {
  const { success } = await logoutRemoteSession();
  if (success) {
    touched();
  }
};

const serverColor = computed<string | null>(() => {
  if (get(customBackendSessionOnly)) {
    return 'primary';
  } else if (get(customBackendSaved)) {
    return 'success';
  }

  return null;
});

const focusElement = (element: any) => {
  if (!element) {
    return;
  }
  const input = element.$el.querySelector(
    'input:not([type=hidden])'
  ) as HTMLInputElement;
  input.focus();
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

const login = async (actions?: {
  syncApproval?: SyncApproval;
  resumeFromBackup?: boolean;
}) => {
  const credentials: LoginCredentials = {
    username: get(username),
    password: get(password),
    ...actions
  };
  emit('login', credentials);
  if (get(rememberUsername)) {
    set(savedUsername, get(username));
  }

  if (get(rememberPassword) && isPackaged) {
    await storePassword(get(username), get(password));
  }
};

const abortLogin = () => {
  resetSyncConflict();
  resetIncompleteUpgradeConflict();
};
</script>

<template>
  <Transition
    enter-class="-top-5 opacity-0"
    enter-to-class="top-0 opacity-1"
    enter-active-class="transform duration-300"
    leave-class="top-0 opacity-1"
    leave-to-class="-top-5 opacity-0"
    leave-active-class="transform duration-100"
  >
    <div :class="css.login">
      <div :class="css.login__wrapper">
        <h4 class="text-h4 mb-3">
          {{ t('login.title') }}
        </h4>

        <div class="text-body-1 text-rui-text-secondary mb-8">
          <p class="mb-3">{{ t('login.description.welcome') }}</p>
          <i18n path="login.description.more_details" tag="p">
            <template #documentation>
              <BaseExternalLink
                :text="t('login.description.our_docs')"
                :href="usageGuideUrl"
                class="underline !text-rui-text-secondary"
              />
            </template>
          </i18n>
        </div>

        <div>
          <form @submit="login()">
            <RuiTextField
              ref="usernameRef"
              v-model="username"
              variant="outlined"
              :label="t('login.label_username')"
              :error-messages="usernameErrors"
              :disabled="loading || conflictExist || customBackendDisplay"
              class="mb-2"
              data-cy="username-input"
            />

            <RuiRevealableTextField
              ref="passwordRef"
              v-model="password"
              variant="outlined"
              :error-messages="passwordErrors"
              :disabled="loading || conflictExist || customBackendDisplay"
              class="mb-2"
              :label="t('login.label_password')"
              data-cy="password-input"
            />

            <div class="flex items-center justify-between">
              <div>
                <RuiCheckbox
                  v-model="rememberUsername"
                  :disabled="
                    customBackendDisplay || rememberPassword || loading
                  "
                  color="primary"
                  hide-details
                  :class="css.remember"
                >
                  {{ t('login.remember_username') }}
                </RuiCheckbox>
                <div
                  v-if="isPackaged"
                  class="pt-2 flex items-center justify-between"
                  no-gutters
                >
                  <div>
                    <RuiCheckbox
                      v-model="rememberPassword"
                      :disabled="customBackendDisplay || loading"
                      color="primary"
                      hide-details
                      :class="css.remember"
                    >
                      {{ t('login.remember_password') }}
                    </RuiCheckbox>
                  </div>
                  <RuiTooltip
                    class="ml-2"
                    :text="t('login.remember_password_tooltip')"
                  >
                    <RuiIcon name="question-line" color="primary" />
                  </RuiTooltip>
                </div>
              </div>
              <div>
                <RuiTooltip
                  :open-delay="400"
                  :text="t('login.custom_backend.tooltip')"
                >
                  <RuiButton
                    :disabled="loading"
                    type="button"
                    icon
                    @click="customBackendDisplay = !customBackendDisplay"
                  >
                    <RuiIcon name="server-line" :color="serverColor" />
                  </RuiButton>
                </RuiTooltip>
              </div>
            </div>

            <Transition
              enter-class="h-0 opacity-0"
              enter-to-class="h-full opacity-1"
              enter-active-class="transition duration-300"
              leave-class="h-full opacity-1"
              leave-to-class="h-0 opacity-0"
              leave-active-class="transition duration-100"
            >
              <div v-if="customBackendDisplay">
                <div class="flex flex-col justify-stretch space-y-4 mt-4">
                  <RuiTextField
                    v-model="customBackendUrl"
                    variant="outlined"
                    :error-messages="
                      v$.customBackendUrl.$errors.map(e => e.$message)
                    "
                    :disabled="customBackendSaved"
                    :label="t('login.custom_backend.label')"
                    :placeholder="t('login.custom_backend.placeholder')"
                    :hint="t('login.custom_backend.hint')"
                  >
                    <template #prepend>
                      <RuiIcon name="server-line" :color="serverColor" />
                    </template>
                    <template #append>
                      <RuiButton
                        v-if="!customBackendSaved"
                        :disabled="loading"
                        variant="text"
                        class="-mr-1 !p-2"
                        type="button"
                        icon
                        @click="saveCustomBackend()"
                      >
                        <RuiIcon name="save-2-fill" color="primary" size="20" />
                      </RuiButton>
                      <RuiButton
                        v-else
                        variant="text"
                        class="-mr-1 !p-2"
                        type="button"
                        icon
                        @click="clearCustomBackend()"
                      >
                        <RuiIcon
                          name="delete-bin-fill"
                          color="primary"
                          size="20"
                        />
                      </RuiButton>
                    </template>
                  </RuiTextField>

                  <RuiCheckbox
                    v-model="customBackendSessionOnly"
                    :class="css.remember"
                    hide-details
                    :disabled="customBackendSaved"
                  >
                    {{ t('login.custom_backend.session_only') }}
                  </RuiCheckbox>
                </div>
              </div>
            </Transition>

            <PremiumSyncConflictAlert
              @proceed="login({ syncApproval: $event })"
            />

            <IncompleteUpgradeAlert
              @confirm="login({ resumeFromBackup: true })"
              @cancel="abortLogin()"
            />

            <div :class="css.login__actions">
              <RuiButton
                color="primary"
                size="lg"
                :disabled="
                  v$.$invalid ||
                  loading ||
                  conflictExist ||
                  customBackendDisplay
                "
                :loading="loading"
                type="submit"
                data-cy="login-submit"
                @click="login()"
              >
                {{ t('common.actions.continue') }}
              </RuiButton>

              <span :class="css.login__actions__footer">
                <span>{{ t('login.button_no_account') }}</span>
                <RuiButton
                  color="primary"
                  size="lg"
                  variant="text"
                  :disabled="loading"
                  type="button"
                  @click="newAccount()"
                >
                  {{ t('login.button_signup') }}
                </RuiButton>
              </span>
            </div>
          </form>
        </div>
      </div>
      <div v-if="hasServerError" class="mt-8 max-w-[41.25rem] mx-auto">
        <RuiAlert
          :action-text="isLoggedInError ? t('login.logout') : ''"
          type="warning"
          @action="logout()"
        >
          <template #title>
            <p class="text-body-2 mb-2">
              <span class="font-bold">
                {{ t('login.credential_error.title') }}
              </span>
              {{ t('login.credential_error.description') }}
            </p>
            <p class="text-body-2 mb-0">
              {{ t('login.credential_error.support') }}
            </p>
          </template>
        </RuiAlert>
      </div>
    </div>
  </Transition>
</template>

<style module lang="scss">
.login {
  &__wrapper {
    @apply max-w-[27.5rem] mx-auto;
  }

  &__actions {
    &__footer {
      @apply flex items-center justify-center;
    }

    @apply flex flex-col justify-stretch space-y-8 pt-8;
  }
}

.remember {
  &__tooltip {
    font-size: 0.8rem;
  }

  @apply ml-2;
}
</style>
