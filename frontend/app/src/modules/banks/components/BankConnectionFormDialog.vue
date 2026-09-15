<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { BankAuthChallenge, BankConnectionIdentity, BankFormData } from '@/modules/banks/types';
import { assert } from '@rotki/common';
import BankConnectionForm from '@/modules/banks/components/BankConnectionForm.vue';
import { useBanks } from '@/modules/banks/use-banks';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

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
const { setMessage } = useMessageStore();
const { t } = useI18n({ useScope: 'global' });

const title = computed<string>(() => {
  if (!isDefined(modelValue))
    return '';
  return get(modelValue).mode === 'edit'
    ? t('bank_settings.dialog.edit.title')
    : t('bank_settings.dialog.add.title');
});

/** Credential slots are snake_case on the wire; the api error keys arrive camelCased. */
function toCamelCase(slot: string): string {
  return slot.replace(/_([a-z])/g, (_match, letter: string) => letter.toUpperCase());
}

/** The api reports credential errors under the slot; the form binds them at `credentials.<slot>`. */
function toFieldErrors(errors: ValidationErrors, form: BankFormData): ValidationErrors {
  const slotsByKey = new Map<string, string>(
    Object.keys(form.credentials).flatMap(slot => [[slot, slot], [toCamelCase(slot), slot]]),
  );
  const mapped: ValidationErrors = {};
  for (const [key, value] of Object.entries(errors)) {
    const slot = slotsByKey.get(key);
    mapped[slot === undefined ? key : `credentials.${slot}`] = value;
  }
  return mapped;
}

async function submit(payload: BankFormData): Promise<boolean | BankAuthChallenge> {
  if (!isDefined(get(authChallenge)))
    return setupBank(payload);
  return answerBankAuthentication(
    { location: payload.location, name: payload.name },
    get(authResponse) || undefined,
  );
}

function reportError(error: unknown, payload: BankFormData): void {
  let errors: string | ValidationErrors = getErrorMessage(error);
  if (error instanceof ApiValidationError) {
    errors = error.getValidationErrors({
      ...payload,
      ...Object.fromEntries(Object.entries(payload.credentials).map(([slot, value]) => [toCamelCase(slot), value])),
    });
  }

  if (typeof errors === 'string') {
    setMessage({
      description: t('bank_settings.errors.setup_message', { bank: payload.location, error: errors }),
      title: t('bank_settings.errors.setup_title'),
    });
  }
  else {
    set(errorMessages, toFieldErrors(errors, payload));
  }
}

async function save(): Promise<void> {
  assert(isDefined(modelValue));
  if (!isDefined(get(authChallenge)) && !get(form)?.validate())
    return;

  set(submitting, true);
  set(errorMessages, {});
  const payload = get(modelValue);

  let result: boolean | BankAuthChallenge | undefined;
  try {
    result = await submit(payload);
  }
  catch (error: unknown) {
    reportError(error, payload);
  }

  set(submitting, false);
  if (result !== true) {
    if (result !== undefined)
      set(authChallenge, result);
    return;
  }
  if (payload.mode !== 'edit')
    emit('added', { location: payload.location, name: payload.name });
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
    :action="{ primary: t('common.actions.save') }"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <div
      v-if="authChallenge"
      class="flex flex-col gap-4"
      data-testid="bank-auth-challenge"
    >
      <RuiAlert type="info">
        {{ authChallenge.challenge ?? authChallenge.prompt }}
      </RuiAlert>
      <img
        v-if="authChallenge.challengeData && authChallenge.challengeMimeType"
        :src="`data:${authChallenge.challengeMimeType};base64,${authChallenge.challengeData}`"
        :alt="authChallenge.prompt"
        class="max-w-full self-center"
      />
      <code
        v-else-if="authChallenge.challengeData"
        class="break-all"
        data-testid="bank-auth-challenge-data"
      >
        {{ authChallenge.challengeData }}
      </code>
      <RuiTextField
        v-if="authChallenge.primitive !== 'app approval poll'"
        v-model="authResponse"
        :label="authChallenge.prompt"
        data-testid="bank-auth-response"
      />
      <p v-else>
        {{ authChallenge.prompt }}
      </p>
    </div>
    <BankConnectionForm
      v-else-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:state-updated="stateUpdated"
      v-model:error-messages="errorMessages"
    />
  </BigDialog>
</template>
