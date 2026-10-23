<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { assert } from '@rotki/common';
import { startPromise } from '@shared/utils';
import BankAuthChallengeFields from '@/modules/banks/components/BankAuthChallengeFields.vue';
import BankConnectionForm from '@/modules/banks/components/BankConnectionForm.vue';
import { type BankAuthChallenge, type BankConnectionIdentity, type BankFormData, type BankSetupError, challengeNeedsResponse, isBankSetupComplete } from '@/modules/banks/types';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBanks } from '@/modules/banks/use-banks';
import BigDialog, { type BigDialogAction } from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<BankFormData | undefined>({ required: true });

const emit = defineEmits<{
  added: [connection: BankConnectionIdentity];
}>();

const submitting = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const errorMessages = ref<ValidationErrors>({});
const authChallenge = ref<BankAuthChallenge>();
const authResponse = ref<string>('');
/** why the backend refused the last save or answer, shown until the next attempt */
const setupError = ref<string>();
const form = useTemplateRef<ComponentExposed<typeof BankConnectionForm>>('form');

const { answerBankAuthentication, cancelBankSetup, setupBank } = useBanks();
const { bankNameFor } = useBankConnectionsStore();
const { t } = useI18n({ useScope: 'global' });

const title = computed<string>(() => {
  if (!isDefined(modelValue))
    return '';
  return get(modelValue).mode === 'edit'
    ? t('bank_settings.dialog.edit.title')
    : t('bank_settings.dialog.add.title');
});

const missingResponse = computed<boolean>(() => {
  const challenge = get(authChallenge);
  return !!challenge && challengeNeedsResponse(challenge) && get(authResponse).trim() === '';
});

const action = computed<BigDialogAction>(() => isDefined(authChallenge)
  ? { disabled: get(missingResponse), primary: t('bank_settings.authentication.continue') }
  : { primary: t('common.actions.save') });

/** The api keys credential errors by slot; the form binds them at `credentials.<slot>`. */
function toFieldErrors(errors: ValidationErrors, form: BankFormData): ValidationErrors {
  return Object.fromEntries(
    Object.entries(errors).map(([key, value]) => [Object.hasOwn(form.credentials, key) ? `credentials.${key}` : key, value]),
  );
}

/**
 * Shows why the backend refused, in the dialog.
 *
 * @remarks
 * A setup whose TAN the bank rejected or let expire is dropped by the backend, so the dialog goes
 * back to the credentials and saving starts a fresh setup. Any other refusal keeps the setup and
 * its challenge, so the answer can be sent again.
 */
function showSetupError(error: BankSetupError, payload: BankFormData): void {
  if (error.type === 'fields') {
    set(errorMessages, toFieldErrors(error.errors, payload));
    return;
  }
  set(setupError, t('bank_settings.errors.setup_message', { bank: bankNameFor(payload.location), error: error.message }));
  if (error.type === 'expired') {
    set(authChallenge, undefined);
    set(authResponse, '');
  }
}

async function save(): Promise<void> {
  assert(isDefined(modelValue));
  if (get(missingResponse) || (!isDefined(authChallenge) && !get(form)?.validate()))
    return;

  set(submitting, true);
  set(errorMessages, {});
  set(setupError, undefined);
  const payload = get(modelValue);
  const outcome = isDefined(get(authChallenge))
    ? await answerBankAuthentication(
        { location: payload.location, name: payload.name },
        get(authResponse).trim() || undefined,
      )
    : await setupBank(payload);
  set(submitting, false);

  if (!outcome.ok) {
    showSetupError(outcome.error, payload);
    return;
  }

  if (!isBankSetupComplete(outcome.value)) {
    set(authChallenge, outcome.value);
    set(authResponse, '');
    return;
  }
  if (payload.mode !== 'edit')
    emit('added', { location: payload.location, name: payload.name });
  set(modelValue, undefined);
  set(authChallenge, undefined);
  set(authResponse, '');
}

/** Closing an add at its TAN step drops the setup, so the next add of that name starts clean. */
function cancel(): void {
  const payload = get(modelValue);
  if (payload && payload.mode !== 'edit' && isDefined(authChallenge))
    startPromise(cancelBankSetup({ location: payload.location, name: payload.name }));
  set(modelValue, undefined);
}

watch(modelValue, (value) => {
  if (!value) {
    set(errorMessages, {});
    set(setupError, undefined);
    set(authChallenge, undefined);
    set(authResponse, '');
    set(stateUpdated, false);
  }
});
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="title"
    :action="action"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="cancel()"
  >
    <div class="flex flex-col gap-4">
      <RuiAlert
        v-if="setupError"
        type="error"
        data-testid="bank-setup-error"
      >
        {{ setupError }}
      </RuiAlert>
      <BankAuthChallengeFields
        v-if="authChallenge"
        v-model:response="authResponse"
        :challenge="authChallenge"
      />
      <BankConnectionForm
        v-else-if="modelValue"
        ref="form"
        v-model="modelValue"
        v-model:state-updated="stateUpdated"
        v-model:error-messages="errorMessages"
      />
    </div>
  </BigDialog>
</template>
