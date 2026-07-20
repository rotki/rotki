<script setup lang="ts">
import type { LoginCredentials, SyncApproval } from '@/modules/auth/login';
import { isValidUrl } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { focusInput } from '@/modules/auth/login/focus-input';
import IncompleteUpgradeAlert from '@/modules/auth/login/IncompleteUpgradeAlert.vue';
import LoginBackendToggle from '@/modules/auth/login/LoginBackendToggle.vue';
import LoginCustomBackendFields from '@/modules/auth/login/LoginCustomBackendFields.vue';
import LoginRememberOptions from '@/modules/auth/login/LoginRememberOptions.vue';
import LoginUsernameField from '@/modules/auth/login/LoginUsernameField.vue';
import LoginWelcomeMessageDialog from '@/modules/auth/login/LoginWelcomeMessageDialog.vue';
import PremiumSyncConflictAlert from '@/modules/auth/login/PremiumSyncConflictAlert.vue';
import { useCustomBackend } from '@/modules/auth/login/use-custom-backend';
import { useLoginRememberOptions } from '@/modules/auth/login/use-login-remember-options';
import { useLogout } from '@/modules/auth/use-logout';
import { useSavedProfiles } from '@/modules/auth/use-saved-profiles';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { toMessages } from '@/modules/core/common/validation/validation';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const {
  errors = [],
  isDocker,
  loading,
} = defineProps<{
  loading: boolean;
  isDocker?: boolean;
  errors?: string[];
}>();

const emit = defineEmits<{
  'touched': [];
  'new-account': [];
  'login': [credentials: LoginCredentials];
  'backend-changed': [url: string | null];
}>();

const { t } = useI18n({ useScope: 'global' });

const { loadProfiles, resolveStoredUsername, savedUsernames } = useSavedProfiles();
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

const usernameFieldRef = useTemplateRef<InstanceType<typeof LoginUsernameField>>('usernameFieldRef');
const passwordRef = useTemplateRef('passwordRef');

const {
  clearBackend,
  display: customBackendDisplay,
  loadBackendSettings,
  modelSessionOnly: customBackendSessionOnly,
  modelUrl: customBackendUrl,
  saveBackend,
  saved: customBackendSaved,
  serverColor,
  toggleDisplay: toggleCustomBackend,
} = useCustomBackend({ onChange: backendChanged });

const {
  loadRememberSettings,
  modelRememberPassword: rememberPassword,
  modelRememberUsername: rememberUsername,
  rememberCredentials,
  storedUsername,
} = useLoginRememberOptions({ isDocker: () => !!isDocker });

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

watch([username, password], ([username, password], [oldUsername, oldPassword]) => {
  // touched should not be emitted when restoring from local storage
  if (!oldUsername && username === get(storedUsername))
    return;

  if (username !== oldUsername || password !== oldPassword)
    touched();
});

const isLoggedInError = useArraySome(() => errors, error => error.includes('is already logged in'));

const usernameError = useArrayFind(() => errors, error => error.startsWith('User '));
const passwordError = useArrayFind(() => errors, error => error.startsWith('Wrong password '));

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

function updateFocus() {
  nextTick(() => {
    if (get(username))
      focusInput(get(passwordRef));
    else
      get(usernameFieldRef)?.focus();
  });
}

// Pre-fills the form and remember toggles for a manual login. The saved-password
// auto-unlock is NOT driven from here anymore — it is a single flow started by
// `useAutoLogin` on backend connect (see use-auto-login.ts / startAuto), so this
// component can never race that flow.
function loadSettings(): void {
  loadRememberSettings();
  if (!get(username))
    set(username, resolveStoredUsername());

  loadBackendSettings();
}

onBeforeMount(async () => {
  await loadProfiles();
  if (get(savedUsernames).length === 0) {
    newAccount();
    return;
  }
  loadSettings();
});

onMounted(() => {
  updateFocus();
});

async function login(actions?: { syncApproval?: SyncApproval; resumeFromBackup?: boolean }) {
  const credentials: LoginCredentials = {
    password: get(password),
    username: get(username),
    ...actions,
  };
  emit('login', credentials);
  await rememberCredentials(get(username), get(password));
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
    <div>
      <div class="max-w-[27.5rem] mx-auto">
        <h4 class="text-h4 mb-3">
          {{ t('login.title') }}
        </h4>

        <div class="text-body-1 text-rui-text-secondary mb-8">
          <p class="mb-3">
            {{ t('login.description.welcome') }}
          </p>
          <i18n-t
            scope="global"
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
            <LoginUsernameField
              ref="usernameFieldRef"
              v-model="username"
              v-model:search="usernameSearch"
              :disabled="loading || conflictExist || customBackendDisplay"
              :loading="loading"
              :is-docker="isDocker"
              :error-messages="usernameErrors"
              @new-account="newAccount()"
            />

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
              <LoginRememberOptions
                v-model:remember-username="rememberUsername"
                v-model:remember-password="rememberPassword"
                :disabled="customBackendDisplay || loading"
                :is-docker="isDocker"
              />
              <LoginBackendToggle
                :open="customBackendDisplay"
                :loading="loading"
                :color="serverColor"
                @toggle="toggleCustomBackend()"
              />
            </div>

            <LoginCustomBackendFields
              v-model:url="customBackendUrl"
              v-model:session-only="customBackendSessionOnly"
              :open="customBackendDisplay"
              :loading="loading"
              :saved="customBackendSaved"
              :color="serverColor"
              :error-messages="toMessages(v$.customBackendUrl)"
              @save="saveBackend()"
              @clear="clearBackend()"
            />

            <PremiumSyncConflictAlert @proceed="login({ syncApproval: $event })" />

            <IncompleteUpgradeAlert
              @confirm="login({ resumeFromBackup: true })"
              @cancel="abortLogin()"
            />

            <div class="flex flex-col justify-stretch space-y-8 pt-6">
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

              <LoginWelcomeMessageDialog :loading="loading" />

              <div class="flex flex-wrap gap-1 sm:gap-0 items-center justify-center text-rui-text-secondary">
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
