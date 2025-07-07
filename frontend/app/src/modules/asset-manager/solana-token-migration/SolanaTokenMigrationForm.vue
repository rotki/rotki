<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import AmountInput from '@/components/inputs/AmountInput.vue';
import { useFormStateWatcher } from '@/composables/form';
import { solanaTokenKindsData } from '@/types/blockchain/chains';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';
import { isValidSolanaAddress } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { required } from '@vuelidate/validators';

interface SolanaTokenMigrationData {
  address: string;
  decimals: number | null;
  tokenKind: string;
}

const modelValue = defineModel<SolanaTokenMigrationData>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

defineProps<{
  loading?: boolean;
  oldAsset?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const address = useRefPropVModel(modelValue, 'address');
const decimals = useRefPropVModel(modelValue, 'decimals');
const tokenKind = useRefPropVModel(modelValue, 'tokenKind');

const decimalsModel = computed({
  get() {
    const value = get(decimals);
    return value !== null ? `${value}` : '';
  },
  set(value: string) {
    const parsedValue = parseDecimals(value);
    set(decimals, parsedValue);
  },
});

const states = {
  address,
  decimals,
  tokenKind,
};

const v$ = useVuelidate({
  address: {
    required,
    validated: (v: string) => !v || isValidSolanaAddress(v),
  },
  decimals: {
    required,
  },
  tokenKind: { required },
}, states, { $autoDirty: true, $externalResults: errors });

useFormStateWatcher(states, stateUpdated);

function parseDecimals(value?: string): number | null {
  if (!value)
    return null;

  const parsedValue = Number.parseInt(value);
  return Number.isNaN(parsedValue) ? null : parsedValue;
}

function clearFieldError(field: keyof SolanaTokenMigrationData) {
  const currentErrors = get(errors);
  if (currentErrors[field]) {
    const { [field]: _, ...rest } = currentErrors;
    set(errors, rest);
  }
}

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div
      v-if="oldAsset"
      class="flex items-center text-caption text-rui-text-secondary -mt-2 mb-4 gap-2"
    >
      <span class="font-medium">{{ t('asset_management.solana_token_migration.migrating_asset') }}:</span>
      <span>{{ oldAsset }}</span>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div
        class="col-span-2"
        data-cy="address-input"
      >
        <RuiTextField
          v-model="address"
          variant="outlined"
          color="primary"
          :error-messages="toMessages(v$.address)"
          :label="t('asset_management.solana_token_migration.solana_address')"
          :disabled="loading"
          @blur="v$.address.$touch()"
          @input="clearFieldError('address')"
        />
      </div>

      <div
        class="col-span-2 md:col-span-1"
        data-cy="decimals-input"
      >
        <AmountInput
          v-model="decimalsModel"
          variant="outlined"
          color="primary"
          integer
          :label="t('asset_form.labels.decimals')"
          :error-messages="toMessages(v$.decimals)"
          :disabled="loading"
          @blur="v$.decimals.$touch()"
          @input="clearFieldError('decimals')"
        />
      </div>

      <div
        class="col-span-2 md:col-span-1"
        data-cy="token-kind-select"
      >
        <RuiMenuSelect
          v-model="tokenKind"
          :label="t('asset_form.labels.token_kind')"
          :options="solanaTokenKindsData"
          :error-messages="toMessages(v$.tokenKind)"
          :disabled="loading"
          key-attr="identifier"
          text-attr="label"
          variant="outlined"
          @update:model-value="clearFieldError('tokenKind')"
        />
      </div>
    </div>
  </div>
</template>
