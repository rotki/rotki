<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import { type LoginCredentials, type SyncApproval } from '@/types/login';

const props = withDefaults(
  defineProps<{
    loading: boolean;
    isDocker?: boolean;
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

const isTest = import.meta.env.VITE_TEST;
const { errors, isDocker } = toRefs(props);

const usersApi = useUsersApi();
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
const usernameSearch: Ref<string> = ref('');
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

const savedUsernames: Ref<string[]> = ref([]);

const orderedUsernamesList = computed(() => {
  const search = get(usernameSearch) || '';
  const usernames = get(savedUsernames);

  if (!search) {
    return usernames;
  }
  return usernames.sort((a, b) => compareTextByKeyword(a, b, search));
});

const hasServerError = computed(
  () => !!get(usernameError) || !!get(passwordError)
);

const usernameErrors = computed(() => {
  const formErrors = [...toMessages(get(v$).username)];
  const serverError = get(usernameError);
  if (serverError) {
    formErrors.push(serverError);
  }

  return formErrors;
});

const passwordErrors = computed(() => {
  const formErrors = [...toMessages(get(v$).password)];
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

const serverColor = computed(() => {
  if (get(customBackendSessionOnly)) {
    return 'primary';
  } else if (get(customBackendSaved)) {
    return 'success';
  }

  return undefined;
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
    !!get(savedRememberUsername) ||
      !!get(savedRememberPassword) ||
      !get(isDocker)
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

const router = useRouter();

onBeforeMount(async () => {
  await loadSettings();
  const profiles = await usersApi.getUserProfiles();
  set(savedUsernames, profiles);
  if (profiles.length === 0) {
    const { currentRoute } = router;
    if (!currentRoute.query.disableNoUserRedirection) {
      newAccount();
    } else {
      await router.replace({ query: {} });
    }
  }
});

onMounted(async () => {
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
    appear
    enter-class="translate-y-5 opacity-0"
    enter-to-class="translate-y-0 opacity-1"
    enter-active-class="transform duration-300"
    leave-class="-translate-y-0 opacity-1"
    leave-to-class="-translate-y-5 opacity-0"
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
              <ExternalLink
                :text="t('login.description.our_docs')"
                :url="usageGuideUrl"
              />
            </template>
          </i18n>
        </div>

        <div>
          <form novalidate @submit.stop.prevent="login()">
            <RuiTextField
              v-if="isDocker || isTest"
              ref="usernameRef"
              v-model="username"
              variant="outlined"
              color="primary"
              autocomplete="username"
              :label="t('login.label_username')"
              :error-messages="usernameErrors"
              :disabled="loading || conflictExist || customBackendDisplay"
              class="mb-2"
              data-cy="username-input"
              dense
            />
            <VAutocomplete
              v-else
              ref="usernameRef"
              v-model="username"
              :search-input.sync="usernameSearch"
              :label="t('login.label_username')"
              :items="orderedUsernamesList"
              :disabled="loading || conflictExist || customBackendDisplay"
              :error-messages="usernameErrors"
              data-cy="username-input"
              class="mb-2"
              auto-select-first
              validate-on-blur
              :hide-no-data="savedUsernames.length > 0"
              clearable
              outlined
              dense
            >
              <template #no-data>
                <div class="px-4 py-2 text-body-2 font-medium">
                  <i18n path="login.no_profiles_found">
                    <template #create_account>
                      <RuiButton
                        color="primary"
                        variant="text"
                        class="text-[1em] py-0 inline px-1"
                        :disabled="loading"
                        type="button"
                        @click="newAccount()"
                      >
                        {{ t('login.button_create_account') }}
                      </RuiButton>
                    </template>
                  </i18n>
                </div>
              </template>
            </VAutocomplete>

            <RuiRevealableTextField
              ref="passwordRef"
              v-model="password"
              variant="outlined"
              color="primary"
              autocomplete="current-password"
              :error-messages="passwordErrors"
              :disabled="loading || conflictExist || customBackendDisplay"
              class="mb-2"
              :label="t('login.label_password')"
              data-cy="password-input"
              dense
            />

            <div class="flex items-center justify-between">
              <div>
                <RuiCheckbox
                  v-if="isDocker"
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
                  class="flex items-center justify-between"
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
                    :open-delay="400"
                    :close-delay="0"
                    class="ml-2"
                    tooltip-class="max-w-[16rem]"
                    :text="t('login.remember_password_tooltip')"
                  >
                    <template #activator>
                      <RuiIcon name="question-line" color="primary" />
                    </template>
                  </RuiTooltip>
                </div>
              </div>
              <RuiTooltip
                :open-delay="400"
                :close-delay="0"
                :text="t('login.custom_backend.tooltip')"
              >
                <template #activator>
                  <RuiButton
                    :disabled="loading"
                    variant="text"
                    type="button"
                    icon
                    @click="customBackendDisplay = !customBackendDisplay"
                  >
                    <RuiIcon name="server-line" :color="serverColor" />
                    <template #append>
                      <RuiIcon
                        size="16"
                        class="-ml-2"
                        :name="
                          customBackendDisplay
                            ? 'arrow-up-s-line'
                            : 'arrow-down-s-line'
                        "
                      />
                    </template>
                  </RuiButton>
                </template>
              </RuiTooltip>
            </div>

            <Transition
              enter-class="h-0 opacity-0"
              enter-to-class="h-full opacity-1"
              enter-active-class="transition duration-300"
              leave-class="h-full opacity-1"
              leave-to-class="h-0 opacity-0"
              leave-active-class="transition duration-100"
            >
              <div
                v-if="customBackendDisplay"
                class="flex flex-col justify-stretch space-y-4 mt-4"
              >
                <RuiTextField
                  v-model="customBackendUrl"
                  color="primary"
                  variant="outlined"
                  :error-messages="toMessages(v$.customBackendUrl)"
                  :disabled="customBackendSaved"
                  :label="t('login.custom_backend.label')"
                  :placeholder="t('login.custom_backend.placeholder')"
                  :hint="t('login.custom_backend.hint')"
                  dense
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
                  color="primary"
                  hide-details
                  :disabled="customBackendSaved"
                >
                  {{ t('login.custom_backend.session_only') }}
                </RuiCheckbox>
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
              >
                {{ t('common.actions.continue') }}
              </RuiButton>

              <div :class="css.login__actions__footer">
                <span>{{ t('login.button_no_account') }}</span>
                <RuiButton
                  color="primary"
                  size="lg"
                  variant="text"
                  :disabled="loading"
                  type="button"
                  data-cy="new-account"
                  class="py-1"
                  @click="newAccount()"
                >
                  {{ t('login.button_create_account') }}
                </RuiButton>
              </div>
            </div>
          </form>
        </div>
      </div>
      <div v-if="errors.length > 0" class="mt-8 max-w-[41.25rem] mx-auto">
        <RuiAlert
          v-if="hasServerError"
          :action-text="isLoggedInError ? t('login.logout') : ''"
          type="error"
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
        <RuiAlert v-else type="error">
          <template #title>
            <p
              v-for="(error, i) in errors"
              :key="i"
              :class="{
                'mb-2': i < errors.length - 1,
                'mb-0': i === errors.length - 1
              }"
            >
              {{ error }}
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
    @apply flex flex-col justify-stretch space-y-8 pt-6;

    &__footer {
      @apply flex items-center justify-center text-rui-text-secondary;
    }
  }
}
</style>
