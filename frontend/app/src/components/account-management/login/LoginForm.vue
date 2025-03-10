<script setup lang="ts">
import type { LoginCredentials, SyncApproval } from '@/types/login';
import IncompleteUpgradeAlert from '@/components/account-management/login/IncompleteUpgradeAlert.vue';
import PremiumSyncConflictAlert from '@/components/account-management/login/PremiumSyncConflictAlert.vue';
import WelcomeMessageDisplay from '@/components/account-management/login/WelcomeMessageDisplay.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { useUsersApi } from '@/composables/api/session/users';
import { useDynamicMessages } from '@/composables/dynamic-messages';
import { useInterop } from '@/composables/electron-interop';
import { useLogout } from '@/modules/account/use-logout';
import { useSessionAuthStore } from '@/store/session/auth';
import { deleteBackendUrl, getBackendUrl, saveBackendUrl } from '@/utils/account-management';
import { compareTextByKeyword } from '@/utils/assets';
import { toMessages } from '@/utils/validation';
import { isValidUrl } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';

const props = withDefaults(
  defineProps<{
    loading: boolean;
    isDocker?: boolean;
    errors?: string[];
  }>(),
  {
    errors: () => [],
  },
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
const { resetIncompleteUpgradeConflict, resetSyncConflict } = authStore;

const touched = () => emit('touched');
const newAccount = () => emit('new-account');
const backendChanged = (url: string | null) => emit('backend-changed', url);

const { logoutRemoteSession } = useLogout();

const username = ref<string>('');
const usernameSearch = ref<string>('');
const password = ref<string>('');
const rememberUsername = ref<boolean>(false);
const rememberPassword = ref<boolean>(false);
const customBackendDisplay = ref<boolean>(false);
const customBackendUrl = ref<string>('');
const customBackendSessionOnly = ref<boolean>(false);
const customBackendSaved = ref<boolean>(false);
const dynamicMessageDialog = ref<boolean>(false);

const usernameRef: Ref = ref();
const passwordRef: Ref = ref();

const savedRememberUsername = useLocalStorage('rotki.remember_username', null);
const savedRememberPassword = useLocalStorage('rotki.remember_password', null);
const savedUsername = useLocalStorage('rotki.username', '');
const { activeWelcomeMessages, welcomeMessage } = useDynamicMessages();

const rules = {
  customBackendUrl: {
    isValidUrl: helpers.withMessage(
      t('login.custom_backend.validation.url'),
      (v: string): boolean => !get(customBackendDisplay) || (v.length < 300 && isValidUrl(v)),
    ),
    required: helpers.withMessage(t('login.custom_backend.validation.non_empty'), requiredIf(customBackendDisplay)),
  },
  password: {
    required: helpers.withMessage(t('login.validation.non_empty_password'), required),
  },
  username: {
    isValidUsername: helpers.withMessage(
      t('login.validation.valid_username'),
      (v: string): boolean => !!(v && /^[\w.-]+$/.test(v)),
    ),
    required: helpers.withMessage(t('login.validation.non_empty_username'), required),
  },
};

const v$ = useVuelidate(
  rules,
  {
    customBackendUrl,
    password,
    username,
  },
  {
    $autoDirty: true,
  },
);

const { clearPassword, getPassword, isPackaged, storePassword } = useInterop();

watch([username, password], ([username, password], [oldUsername, oldPassword]) => {
  // touched should not be emitted when restoring from local storage
  if (!oldUsername && username === get(savedUsername))
    return;

  if (username !== oldUsername || password !== oldPassword)
    touched();
});

const isLoggedInError = useArraySome(errors, error => error.includes('is already logged in'));

const usernameError = useArrayFind(errors, error => error.startsWith('User '));
const passwordError = useArrayFind(errors, error => error.startsWith('Wrong password '));

const savedUsernames = ref<string[]>([]);

const orderedUsernamesList = computed(() => {
  const search = get(usernameSearch) || '';
  const usernames = get(savedUsernames);

  if (!search)
    return usernames;

  return usernames.sort((a, b) => compareTextByKeyword(a, b, search));
});

const hasServerError = computed(() => !!get(usernameError) || !!get(passwordError));

const usernameErrors = computed(() => {
  const formErrors = [...toMessages(get(v$).username)];
  const serverError = get(usernameError);
  if (serverError)
    formErrors.push(serverError);

  return formErrors;
});

const passwordErrors = computed(() => {
  const formErrors = [...toMessages(get(v$).password)];
  const serverError = get(passwordError);
  if (serverError)
    formErrors.push(serverError);

  return formErrors;
});

async function logout() {
  const { success } = await logoutRemoteSession();
  if (success)
    touched();
}

const serverColor = computed(() => {
  if (get(customBackendSessionOnly))
    return 'primary';
  else if (get(customBackendSaved))
    return 'success';

  return undefined;
});

function focusElement(element: any) {
  if (!element)
    return;

  const input = element.$el.querySelector('input:not([type=hidden])') as HTMLInputElement;
  input.focus();
}

function updateFocus() {
  nextTick(() => {
    focusElement(get(username) ? get(passwordRef) : get(usernameRef));
  });
}

function saveCustomBackend() {
  saveBackendUrl({
    sessionOnly: get(customBackendSessionOnly),
    url: get(customBackendUrl),
  });
  backendChanged(get(customBackendUrl));
  set(customBackendSaved, true);
  set(customBackendDisplay, false);
}

function clearCustomBackend() {
  set(customBackendUrl, '');
  set(customBackendSessionOnly, false);
  deleteBackendUrl();
  backendChanged(null);
  set(customBackendSaved, false);
  set(customBackendDisplay, false);
}

function checkRememberUsername() {
  set(rememberUsername, !!get(savedRememberUsername) || !!get(savedRememberPassword) || !get(isDocker));
}

async function loadSettings() {
  set(rememberPassword, !!get(savedRememberPassword));
  checkRememberUsername();
  set(username, get(savedUsername));
  const { sessionOnly, url } = getBackendUrl();
  set(customBackendUrl, url);
  set(customBackendSessionOnly, sessionOnly);
  set(customBackendSaved, !!url);

  if (get(errors).length > 0)
    return;

  if (isPackaged && get(rememberPassword) && get(username)) {
    const savedPassword = await getPassword(get(username));

    if (savedPassword) {
      set(password, savedPassword);
      await login();
    }
  }
}

const router = useRouter();

onBeforeMount(async () => {
  await loadSettings();
  const profiles = await usersApi.getUserProfiles();
  set(savedUsernames, profiles);
  if (profiles.length === 0) {
    const { currentRoute } = router;
    if (!get(currentRoute).query.disableNoUserRedirection)
      newAccount();
    else await router.replace({ query: {} });
  }
});

onMounted(() => {
  updateFocus();
});

watch(rememberUsername, (remember: boolean, previous: boolean) => {
  if (remember === previous)
    return;

  if (!remember) {
    set(savedRememberUsername, null);
    set(savedUsername, null);
  }
  else {
    set(savedRememberUsername, 'true');
  }
});

watch(rememberPassword, async (remember: boolean, previous: boolean) => {
  if (remember === previous)
    return;

  if (!remember) {
    set(savedRememberPassword, null);
    if (isPackaged)
      await clearPassword();
  }
  else {
    set(savedRememberPassword, 'true');
  }

  checkRememberUsername();
});

async function login(actions?: { syncApproval?: SyncApproval; resumeFromBackup?: boolean }) {
  const credentials: LoginCredentials = {
    password: get(password),
    username: get(username),
    ...actions,
  };
  emit('login', credentials);
  if (get(rememberUsername))
    set(savedUsername, get(username));

  if (get(rememberPassword) && isPackaged)
    await storePassword(get(username), get(password));
}

function abortLogin() {
  resetSyncConflict();
  resetIncompleteUpgradeConflict();
}
</script>

<template>
  <Transition
    appear
    enter-from-class="translate-y-5 opacity-0"
    enter-to-class="translate-y-0 opacity-1"
    enter-active-class="transform duration-300"
    leave-from-class="-translate-y-0 opacity-1"
    leave-to-class="-translate-y-5 opacity-0"
    leave-active-class="transform duration-100"
  >
    <div :class="$style.login">
      <div :class="$style.login__wrapper">
        <h4 class="text-h4 mb-3">
          {{ t('login.title') }}
        </h4>

        <div class="text-body-1 text-rui-text-secondary mb-8">
          <p class="mb-3">
            {{ t('login.description.welcome') }}
          </p>
          <i18n-t
            keypath="login.description.more_details"
            tag="p"
          >
            <template #documentation>
              <ExternalLink
                :text="t('login.description.our_docs')"
                :url="externalLinks.usageGuide"
              />
            </template>
          </i18n-t>
        </div>

        <div>
          <form
            novalidate
            @submit.stop.prevent="login()"
          >
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
            <RuiAutoComplete
              v-else
              ref="usernameRef"
              v-model="username"
              v-model:search-input="usernameSearch"
              :label="t('login.label_username')"
              :options="orderedUsernamesList"
              :disabled="loading || conflictExist || customBackendDisplay"
              :error-messages="usernameErrors"
              data-cy="username-input"
              class="mb-2 [&_[data-id=activator]]:bg-transparent"
              auto-select-first
              :hide-no-data="savedUsernames.length > 0"
              clearable
              variant="outlined"
              :item-height="38"
              dense
            >
              <template #item="{ item }">
                <div class="py-1">
                  {{ item }}
                </div>
              </template>
              <template #no-data>
                <div class="px-4 py-2 text-body-2 font-medium">
                  <i18n-t keypath="login.no_profiles_found">
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
                  </i18n-t>
                </div>
              </template>
            </RuiAutoComplete>

            <RuiRevealableTextField
              ref="passwordRef"
              v-model="password"
              variant="outlined"
              color="primary"
              autocomplete="current-password"
              :error-messages="passwordErrors"
              :disabled="loading || conflictExist || customBackendDisplay"
              class="mb-2 [&>div]:bg-transparent"
              :label="t('login.label_password')"
              data-cy="password-input"
              dense
            />

            <div class="flex items-center justify-between">
              <div>
                <RuiCheckbox
                  v-if="isDocker"
                  v-model="rememberUsername"
                  :disabled="customBackendDisplay || rememberPassword || loading"
                  color="primary"
                  hide-details
                  :class="$style.remember"
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
                      :class="$style.remember"
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
                      <RuiIcon
                        name="lu-circle-help"
                        color="primary"
                      />
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
                    <RuiIcon
                      name="lu-server"
                      :color="serverColor"
                    />
                    <template #append>
                      <RuiIcon
                        size="16"
                        class="-ml-2"
                        :name="customBackendDisplay ? 'lu-chevron-up' : 'lu-chevron-down'"
                      />
                    </template>
                  </RuiButton>
                </template>
              </RuiTooltip>
            </div>

            <RuiAccordion :open="customBackendDisplay">
              <div
                v-if="customBackendDisplay"
                class="flex flex-col justify-stretch space-y-4 pt-4"
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
                  class="[&>div]:bg-transparent"
                  dense
                >
                  <template #prepend>
                    <RuiIcon
                      name="lu-server"
                      :color="serverColor"
                    />
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
                      <RuiIcon
                        name="lu-save"
                        color="primary"
                        size="20"
                      />
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
                        name="lu-trash-2"
                        color="primary"
                        size="20"
                      />
                    </RuiButton>
                  </template>
                </RuiTextField>

                <RuiCheckbox
                  v-model="customBackendSessionOnly"
                  :class="$style.remember"
                  color="primary"
                  hide-details
                  :disabled="customBackendSaved"
                >
                  {{ t('login.custom_backend.session_only') }}
                </RuiCheckbox>
              </div>
            </RuiAccordion>

            <PremiumSyncConflictAlert @proceed="login({ syncApproval: $event })" />

            <IncompleteUpgradeAlert
              @confirm="login({ resumeFromBackup: true })"
              @cancel="abortLogin()"
            />

            <div :class="$style.login__actions">
              <RuiButton
                color="primary"
                size="lg"
                :disabled="v$.$invalid || loading || conflictExist || customBackendDisplay"
                :loading="loading"
                type="submit"
                data-cy="login-submit"
              >
                {{ t('common.actions.continue') }}
              </RuiButton>

              <RuiDialog
                v-if="welcomeMessage && welcomeMessage.action"
                v-model="dynamicMessageDialog"
                max-width="400"
              >
                <template #activator="{ attrs }">
                  <RuiButton
                    color="primary"
                    class="lg:hidden w-full"
                    size="lg"
                    :disabled="loading"
                    variant="outlined"
                    type="button"
                    data-cy="show-dynamic-messages"
                    v-bind="attrs"
                  >
                    {{ welcomeMessage.action.text }}
                  </RuiButton>
                </template>

                <RuiCard>
                  <WelcomeMessageDisplay
                    class="!bg-transparent !p-0"
                    :messages="activeWelcomeMessages"
                  />

                  <template #footer>
                    <div class="w-full" />
                    <RuiButton
                      color="primary"
                      variant="text"
                      @click="dynamicMessageDialog = false"
                    >
                      {{ t('common.actions.close') }}
                    </RuiButton>
                  </template>
                </RuiCard>
              </RuiDialog>

              <div :class="$style.login__actions__footer">
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
      <div
        v-if="errors.length > 0"
        class="mt-8 max-w-[41.25rem] mx-auto"
      >
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
        <RuiAlert
          v-else
          type="error"
        >
          <template #title>
            <p
              v-for="(error, i) in errors"
              :key="i"
              :class="{
                'mb-2': i < errors.length - 1,
                'mb-0': i === errors.length - 1,
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
      @apply flex flex-wrap gap-1 sm:gap-0 items-center justify-center text-rui-text-secondary;
    }
  }
}
</style>
