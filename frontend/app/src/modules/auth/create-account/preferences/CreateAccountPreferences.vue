<script lang="ts" setup>
import type { PremiumSetup } from '@/modules/auth/login';
import { type SupportedCurrency, useCurrencies } from '@/modules/assets/amount-display/currencies';
import CreateAccountAnalyticsOption from '@/modules/auth/create-account/CreateAccountAnalyticsOption.vue';
import CreateAccountStepActions from '@/modules/auth/create-account/CreateAccountStepActions.vue';
import CreateAccountErrorAlert from '@/modules/auth/create-account/errors/CreateAccountErrorAlert.vue';
import CreateAccountPremiumSection
  from '@/modules/auth/create-account/preferences/CreateAccountPremiumSection.vue';
import { useStepCheck } from '@/modules/auth/create-account/use-step-check';

const mainCurrency = defineModel<SupportedCurrency>('mainCurrency', { required: true });
const submitUsageAnalytics = defineModel<boolean>('submitUsageAnalytics', { required: true });
const premiumEnabled = defineModel<boolean>('premiumEnabled', { required: true });
const premiumForm = defineModel<PremiumSetup>('premiumForm', { required: true });
const premiumShouldSync = defineModel<boolean>('premiumShouldSync', { required: true });

const { error = '' } = defineProps<{
  loading: boolean;
  error?: string;
}>();

const emit = defineEmits<{
  back: [];
  confirm: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { currencies } = useCurrencies();

const premium = useTemplateRef<InstanceType<typeof CreateAccountPremiumSection>>('premium');

const { issueCount, validate } = useStepCheck(premium);

const currencyOptions = computed<{ key: SupportedCurrency; label: string }[]>(() =>
  get(currencies)
    .filter(currency => !currency.crypto)
    .map(currency => ({ key: currency.tickerSymbol, label: `${currency.tickerSymbol}, ${currency.name}` })),
);

async function confirm(): Promise<void> {
  if (await validate())
    emit('confirm');
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <p class="text-body-1 text-rui-text-secondary">
      {{ t('create_account.preferences.description') }}
    </p>
    <RuiMenuSelect
      v-model="mainCurrency"
      data-testid="create-account-main-currency"
      :label="t('create_account.preferences.main_currency')"
      :hint="t('create_account.preferences.main_currency_hint')"
      :options="currencyOptions"
      key-attr="key"
      text-attr="label"
      :disabled="loading"
    />
    <CreateAccountAnalyticsOption
      v-model="submitUsageAnalytics"
      :loading="loading"
    />
    <CreateAccountPremiumSection
      ref="premium"
      v-model:expanded="premiumEnabled"
      v-model:form="premiumForm"
      v-model:should-sync="premiumShouldSync"
      :loading="loading"
    />
    <CreateAccountErrorAlert
      v-if="error"
      :error="error"
    />
    <CreateAccountStepActions
      :next-label="t('create_account.actions.create_profile')"
      next-test-id="create-account-submit"
      :issue-count="issueCount"
      :loading="loading"
      @back="emit('back')"
      @next="confirm()"
    />
  </div>
</template>
