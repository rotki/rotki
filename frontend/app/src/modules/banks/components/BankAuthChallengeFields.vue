<script setup lang="ts">
import { type BankAuthChallenge, challengeNeedsResponse } from '@/modules/banks/types';

const response = defineModel<string>('response', { required: true });

const { challenge } = defineProps<{
  challenge: BankAuthChallenge;
}>();

const { t } = useI18n({ useScope: 'global' });

const headline = computed<string>(() => challenge.challenge ?? challenge.prompt);

const showsPrompt = computed<boolean>(() => challenge.prompt !== get(headline));

const image = computed<string | undefined>(() => challenge.challengeData && challenge.challengeMimeType
  ? `data:${challenge.challengeMimeType};base64,${challenge.challengeData}`
  : undefined);
</script>

<template>
  <div
    class="flex flex-col gap-4"
    data-testid="bank-auth-challenge"
  >
    <RuiAlert
      type="info"
      data-testid="bank-auth-headline"
    >
      {{ headline }}
    </RuiAlert>
    <img
      v-if="image"
      :src="image"
      :alt="challenge.prompt"
      class="max-w-full self-center"
      data-testid="bank-auth-challenge-image"
    />
    <code
      v-else-if="challenge.challengeData"
      class="break-all"
      data-testid="bank-auth-challenge-data"
    >
      {{ challenge.challengeData }}
    </code>
    <RuiTextField
      v-if="challengeNeedsResponse(challenge)"
      v-model="response"
      variant="outlined"
      color="primary"
      :label="t('bank_settings.authentication.response')"
      :hint="showsPrompt ? challenge.prompt : undefined"
      data-testid="bank-auth-response"
    />
    <p
      v-else-if="showsPrompt"
      data-testid="bank-auth-prompt"
    >
      {{ challenge.prompt }}
    </p>
  </div>
</template>
