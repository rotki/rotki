import type { ZodType } from 'zod';
import { useArraySome, watchImmediate } from '@vueuse/core';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type MaybeRefOrGetter, type Ref, toValue, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { classifyLoginErrors, type LoginFormState, loginSchema } from '@/modules/auth/login/login-form';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { type FormApi, noSubmit, useForm } from '@/modules/core/form/use-form';

interface UseLoginFormValidationOptions {
  /** The backend's rejection messages, routed onto the field each one names. */
  errors: MaybeRefOrGetter<string[]>;
  /** Whether a login is in flight, which blocks submitting. */
  loading: MaybeRefOrGetter<boolean>;
  /** Whether the custom backend panel is open, which adds the url rules and blocks submitting. */
  customBackendDisplay: MaybeRefOrGetter<boolean>;
  /** The url the backend panel's composable owns, mirrored into the form state. */
  customBackendUrl: MaybeRefOrGetter<string>;
  /** The username restored from storage, whose restore is not a user edit. */
  storedUsername: MaybeRefOrGetter<string>;
  /** Called when the user edits the username or password. */
  onTouched: () => void;
}

interface UseLoginFormValidationReturn {
  /** The form state, bound to the username and password fields. */
  modelState: FormApi<LoginFormState, LoginFormState>['state'];
  /** Visible messages for a field. */
  fieldErrors: FormApi<LoginFormState, LoginFormState>['errors'];
  /** Marks a field as touched, so its errors show. */
  touch: FormApi<LoginFormState, LoginFormState>['touch'];
  /** Replaces the backend field errors. */
  setServerErrors: FormApi<LoginFormState, LoginFormState>['setServerErrors'];
  /** The backend's rejection messages, keyed by the field each one names. */
  serverErrors: ComputedRef<Record<string, string[]>>;
  /** Whether the rejection is about the credentials, which is what picks the actionable alert. */
  hasServerError: ComputedRef<boolean>;
  /** Whether the rejection says another client holds the session. */
  isLoggedInError: ComputedRef<boolean>;
  /** Whether a sync or incomplete-upgrade conflict waits on the user. */
  conflictExist: Readonly<Ref<boolean>>;
  /** Whether the submit button is disabled. */
  submitDisabled: ComputedRef<boolean>;
}

/**
 * Owns the login form's state and validation: the schema, the backend errors routed onto fields,
 * the custom backend url mirrored into the state, and whether the form can be submitted.
 */
export function useLoginFormValidation(options: UseLoginFormValidationOptions): UseLoginFormValidationReturn {
  const { customBackendDisplay, customBackendUrl, errors, loading, onTouched, storedUsername } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { conflictExist } = storeToRefs(useSessionAuthStore());

  const schema = computed<ZodType>(() => loginSchema({
    emptyPassword: t('login.validation.non_empty_password'),
    emptyUrl: t('login.custom_backend.validation.non_empty'),
    invalidUrl: t('login.custom_backend.validation.url'),
    invalidUsername: t('login.validation.valid_username'),
    requiredUsername: t('login.validation.non_empty_username'),
  }, toValue(customBackendDisplay)));

  const {
    errors: fieldErrors,
    setServerErrors,
    state,
    touch,
    valid: parses,
  } = useForm<LoginFormState, LoginFormState>({
    initial: (): LoginFormState => ({ customBackendUrl: '', password: '', username: '' }),
    schema,
    submit: noSubmit,
    transform: (current): LoginFormState => ({ ...current }),
  });

  const serverErrors = computed<Record<string, string[]>>(() => classifyLoginErrors(toValue(errors)));

  const hasServerError = computed<boolean>(() => Object.keys(get(serverErrors)).length > 0);

  const isLoggedInError = useArraySome(() => toValue(errors), error => error.includes('is already logged in'));

  const submitDisabled = computed<boolean>(() =>
    !get(parses) || toValue(loading) || get(conflictExist) || toValue(customBackendDisplay),
  );

  watch(() => [state.username, state.password], ([username, password], [oldUsername, oldPassword]) => {
    const restoredFromLocalStorage = !oldUsername && username === toValue(storedUsername);
    if (restoredFromLocalStorage)
      return;

    if (username !== oldUsername || password !== oldPassword)
      onTouched();
  });

  /**
   * Copies the url the backend panel's composable owns into the form state, so it is validated
   * alongside the credentials.
   *
   * @remarks
   * Touch is deliberately left out of this: an untouched empty url has to stay silent until the user
   * has actually been in the field.
   *
   * @param url - the url the panel currently holds
   */
  function mirrorBackendUrl(url: string): void {
    state.customBackendUrl = url;
  }

  watchImmediate(() => toValue(customBackendUrl), mirrorBackendUrl);

  watch(() => toValue(customBackendUrl), () => {
    touch('customBackendUrl');
  });

  watchImmediate(serverErrors, (value) => {
    setServerErrors(value);
  }, { deep: true });

  return {
    conflictExist,
    fieldErrors,
    hasServerError,
    isLoggedInError,
    modelState: state,
    serverErrors,
    setServerErrors,
    submitDisabled,
    touch,
  };
}
