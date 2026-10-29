<script setup lang="ts">
import { startPromise } from '@shared/utils';
import BankAuthChallengeFields from '@/modules/banks/components/BankAuthChallengeFields.vue';
import { type BankAuthenticationRequest, type BankSetupError, challengeNeedsResponse, isBankSetupComplete } from '@/modules/banks/types';
import { useBanks } from '@/modules/banks/use-banks';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<BankAuthenticationRequest>();

const response = ref<string>('');
const submitting = ref<boolean>(false);
/** why the bank refused the last answer, shown in the dialog until the user types again */
const error = ref<string>();
/** the bank dropped the challenge, so only a new sync can raise another one */
const expired = ref<boolean>(false);

const { answerBankAuthentication, syncBanks } = useBanks();
const { t } = useI18n({ useScope: 'global' });

const missingResponse = computed<boolean>(() => {
  const request = get(modelValue);
  return !!request && challengeNeedsResponse(request.challenge) && get(response).trim() === '';
});

const primaryAction = computed<string>(() => get(expired)
  ? t('bank_settings.authentication.sync_again')
  : t('bank_settings.authentication.continue'));

function errorText(setupError: BankSetupError): string {
  return setupError.type === 'fields'
    ? Object.values(setupError.errors).flat().join(', ')
    : setupError.message;
}

function close(): void {
  set(modelValue, undefined);
  set(response, '');
  set(error, undefined);
  set(expired, false);
}

function syncAgain({ identifier }: BankAuthenticationRequest): void {
  startPromise(syncBanks({ identifier }));
  close();
}

async function confirm(): Promise<void> {
  const request = get(modelValue);
  if (!request)
    return;
  if (get(expired)) {
    syncAgain(request);
    return;
  }
  if (get(missingResponse))
    return;

  set(error, undefined);
  set(submitting, true);
  const result = await answerBankAuthentication(
    { identifier: request.identifier },
    get(response).trim() || undefined,
  );
  set(submitting, false);

  if (!result.ok) {
    set(error, errorText(result.error));
    set(expired, result.error.type === 'expired');
    return;
  }

  if (isBankSetupComplete(result.value)) {
    close();
    return;
  }
  set(modelValue, { ...request, challenge: result.value });
  set(response, '');
}

watch(response, () => {
  if (!get(expired))
    set(error, undefined);
});
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="modelValue?.name ?? ''"
    :action="{ primary: primaryAction, disabled: !expired && missingResponse }"
    :loading="submitting"
    @confirm="confirm()"
    @cancel="close()"
  >
    <div class="flex flex-col gap-4">
      <RuiAlert
        v-if="error"
        type="error"
        data-testid="bank-auth-error"
      >
        {{ expired ? t('bank_settings.authentication.expired', { error }) : error }}
      </RuiAlert>
      <BankAuthChallengeFields
        v-if="modelValue && !expired"
        v-model:response="response"
        :challenge="modelValue.challenge"
      />
    </div>
  </BigDialog>
</template>
