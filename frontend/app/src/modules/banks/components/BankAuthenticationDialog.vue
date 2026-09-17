<script setup lang="ts">
import BankAuthChallengeFields from '@/modules/banks/components/BankAuthChallengeFields.vue';
import { type BankAuthenticationRequest, challengeNeedsResponse, isBankSetupComplete } from '@/modules/banks/types';
import { useBanks } from '@/modules/banks/use-banks';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<BankAuthenticationRequest>();

const response = ref<string>('');
const submitting = ref<boolean>(false);

const { answerBankAuthentication } = useBanks();
const { setMessage } = useMessageStore();
const { t } = useI18n({ useScope: 'global' });

const missingResponse = computed<boolean>(() => {
  const request = get(modelValue);
  return !!request && challengeNeedsResponse(request.challenge) && get(response).trim() === '';
});

function close(): void {
  set(modelValue, undefined);
  set(response, '');
}

async function confirm(): Promise<void> {
  const request = get(modelValue);
  if (!request || get(missingResponse))
    return;

  set(submitting, true);
  const result = await answerBankAuthentication(
    { location: request.location, name: request.name },
    get(response).trim() || undefined,
  );
  set(submitting, false);

  if (!result.ok) {
    setMessage({
      description: result.error.type === 'rejected'
        ? result.error.message
        : Object.values(result.error.errors).flat().join(', '),
      title: t('bank_settings.errors.setup_title'),
    });
    return;
  }

  if (isBankSetupComplete(result.value)) {
    close();
    return;
  }
  set(modelValue, { ...request, challenge: result.value });
  set(response, '');
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="modelValue?.name ?? ''"
    :action="{ primary: t('bank_settings.authentication.continue'), disabled: missingResponse }"
    :loading="submitting"
    @confirm="confirm()"
    @cancel="close()"
  >
    <BankAuthChallengeFields
      v-if="modelValue"
      v-model:response="response"
      :challenge="modelValue.challenge"
    />
  </BigDialog>
</template>
