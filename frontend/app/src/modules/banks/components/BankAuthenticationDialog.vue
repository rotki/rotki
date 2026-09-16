<script setup lang="ts">
import { type BankAuthenticationRequest, isBankSetupComplete } from '@/modules/banks/types';
import { useBanks } from '@/modules/banks/use-banks';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<BankAuthenticationRequest>();

const emit = defineEmits<{
  authenticated: [];
}>();

const response = ref<string>('');
const submitting = ref<boolean>(false);

const { answerBankAuthentication } = useBanks();
const { setMessage } = useMessageStore();
const { t } = useI18n({ useScope: 'global' });

async function confirm(): Promise<void> {
  const request = get(modelValue);
  if (!request)
    return;

  set(submitting, true);
  try {
    const result = await answerBankAuthentication(request, get(response) || undefined);
    if (result.ok && isBankSetupComplete(result.value)) {
      set(modelValue, undefined);
      set(response, '');
      emit('authenticated');
    }
    else if (result.ok) {
      set(modelValue, { ...request, challenge: result.value });
    }
    else {
      throw new Error(
        result.error.type === 'rejected'
          ? result.error.message
          : Object.values(result.error.errors).flat().join(', '),
      );
    }
  }
  catch (error: unknown) {
    setMessage({
      description: getErrorMessage(error),
      title: t('bank_settings.errors.setup_title'),
    });
  }
  finally {
    set(submitting, false);
  }
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="modelValue?.name ?? ''"
    :action="{ primary: t('common.actions.save') }"
    :loading="submitting"
    @confirm="confirm()"
    @cancel="modelValue = undefined"
  >
    <div
      v-if="modelValue"
      class="flex flex-col gap-4"
      data-testid="bank-auth-challenge"
    >
      <RuiAlert type="info">
        {{ modelValue.challenge.challenge ?? modelValue.challenge.prompt }}
      </RuiAlert>
      <img
        v-if="modelValue.challenge.challengeData && modelValue.challenge.challengeMimeType"
        :src="`data:${modelValue.challenge.challengeMimeType};base64,${modelValue.challenge.challengeData}`"
        :alt="modelValue.challenge.prompt"
        class="max-w-full self-center"
      />
      <code
        v-else-if="modelValue.challenge.challengeData"
        class="break-all"
        data-testid="bank-auth-challenge-data"
      >
        {{ modelValue.challenge.challengeData }}
      </code>
      <RuiTextField
        v-if="modelValue.challenge.primitive !== 'app approval poll'"
        v-model="response"
        :label="modelValue.challenge.prompt"
        data-testid="bank-auth-response"
      />
      <p v-else>
        {{ modelValue.challenge.prompt }}
      </p>
    </div>
  </BigDialog>
</template>
