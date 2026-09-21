<script setup lang="ts">
import type { ResultAsync } from 'plainfp/result-async';
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { assert } from '@rotki/common';
import BankAuthChallengeFields from '@/modules/banks/components/BankAuthChallengeFields.vue';
import BankConnectionForm from '@/modules/banks/components/BankConnectionForm.vue';
import { type BankAuthChallenge, type BankConnectionIdentity, type BankFormData, type BankSetupError, type BankSetupResult, challengeNeedsResponse, isBankSetupComplete } from '@/modules/banks/types';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBanks } from '@/modules/banks/use-banks';
import { useMessageStore } from '@/modules/core/common/use-message-store';
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
const form = useTemplateRef<ComponentExposed<typeof BankConnectionForm>>('form');

const { answerBankAuthentication, setupBank } = useBanks();
const { bankNameFor } = useBankConnectionsStore();
const { setMessage } = useMessageStore();
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

function showSetupError(error: BankSetupError, payload: BankFormData): void {
  if (error.type === 'fields') {
    set(errorMessages, toFieldErrors(error.errors, payload));
    return;
  }
  setMessage({
    description: t('bank_settings.errors.setup_message', { bank: bankNameFor(payload.connector), error: error.message }),
    title: t('bank_settings.errors.setup_title'),
  });
}

/** Answers the pending challenge of the connection being set up, or starts the setup. */
async function submit(payload: BankFormData): ResultAsync<BankSetupResult, BankSetupError> {
  const identifier = get(authChallenge)?.identifier;
  return identifier
    ? answerBankAuthentication({ identifier }, get(authResponse).trim() || undefined)
    : setupBank(payload);
}

async function save(): Promise<void> {
  assert(isDefined(modelValue));
  if (get(missingResponse) || (!isDefined(authChallenge) && !get(form)?.validate()))
    return;

  set(submitting, true);
  set(errorMessages, {});
  const payload = get(modelValue);
  const outcome = await submit(payload);
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
  if (outcome.value !== true)
    emit('added', { identifier: outcome.value.identifier, location: payload.location, name: payload.name });
  set(modelValue, undefined);
  set(authChallenge, undefined);
  set(authResponse, '');
}

watch(modelValue, (value) => {
  if (!value) {
    set(errorMessages, {});
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
    @cancel="modelValue = undefined"
  >
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
  </BigDialog>
</template>
