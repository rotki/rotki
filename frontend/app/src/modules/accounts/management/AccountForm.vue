<script setup lang="ts">
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { assert } from '@rotki/common';
import { startPromise } from '@shared/utils';
import AccountFormApiKeyAlertContent from '@/modules/accounts/management/AccountFormApiKeyAlertContent.vue';
import AccountSelector from '@/modules/accounts/management/inputs/AccountSelector.vue';
import AddressAccountForm from '@/modules/accounts/management/types/AddressAccountForm.vue';
import AgnosticAddressAccountForm from '@/modules/accounts/management/types/AgnosticAddressAccountForm.vue';
import BtcAccountForm from '@/modules/accounts/management/types/BtcAccountForm.vue';
import ValidatorAccountForm from '@/modules/accounts/management/types/ValidatorAccountForm.vue';
import { useAccountFormState } from '@/modules/accounts/management/use-account-form-state';
import { useAccountFormWarnings } from '@/modules/accounts/management/use-account-form-warnings';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

const modelValue = defineModel<AccountManageState>({ required: true });

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

defineProps<{
  loading: boolean;
  chainIds: string[];
}>();

const { t } = useI18n({ useScope: 'global' });

const form = useTemplateRef<
  | InstanceType<typeof AddressAccountForm>
  | InstanceType<typeof ValidatorAccountForm>
  | InstanceType<typeof BtcAccountForm>
>('form');

const { getChainName } = useSupportedChains();

const { handleDetectedAddress, handleDetectedXpub, selectChain, setValidator } = useAccountFormState(modelValue);

const {
  beaconchainInfo,
  hasMultipleWarnings,
  hiddenWarningCount,
  toggleWarningExpanded,
  visibleWarnings,
  warningExpanded,
  warnings,
} = useAccountFormWarnings(modelValue);

const chain = computed<string | undefined>(() => get(modelValue).chain);

async function validate(): Promise<boolean> {
  const selectedForm = get(form);
  assert(selectedForm);
  if ('validate' in selectedForm)
    return await selectedForm.validate();

  logger.debug('selected form does not implement validate default to true');
  return true;
}

defineExpose({
  validate,
});
</script>

<template>
  <div data-testid="blockchain-balance-form">
    <RuiAlert
      v-if="beaconchainInfo?.service"
      type="info"
      class="mb-6 -mt-2"
    >
      <AccountFormApiKeyAlertContent :service="beaconchainInfo.service" />
    </RuiAlert>

    <RuiAlert
      v-if="warnings.length > 0"
      type="warning"
      class="mb-6 -mt-2"
    >
      <ul :class="hasMultipleWarnings ? 'list-disc pl-4 space-y-1' : 'list-none pl-0'">
        <li
          v-for="warning in visibleWarnings"
          :key="warning.type"
        >
          <template v-if="warning.type === 'apiKey' && warning.service">
            <AccountFormApiKeyAlertContent :service="warning.service" />
          </template>
          <template v-else-if="warning.type === 'solana'">
            {{ t('blockchain_balances.solana_warning') }}
          </template>
          <template v-else-if="warning.type === 'earlyChain' && warning.chain">
            {{ t('blockchain_balances.early_chain_warning', { chain: getChainName(warning.chain) }) }}
          </template>
          <template v-else-if="warning.type === 'binance'">
            {{ t('blockchain_balances.binance_warning') }}
          </template>
        </li>
      </ul>

      <RuiButton
        v-if="hasMultipleWarnings"
        variant="text"
        color="warning"
        size="sm"
        class="mt-1 -mb-1 ml-2.5"
        @click="toggleWarningExpanded()"
      >
        {{ warningExpanded ? t('common.actions.show_less') : t('common.actions.show_more_num', { count: hiddenWarningCount }) }}
        <template #append>
          <RuiIcon
            :name="warningExpanded ? 'lu-chevron-up' : 'lu-chevron-down'"
            size="16"
          />
        </template>
      </RuiButton>
    </RuiAlert>

    <AccountSelector
      :chain="chain"
      :chain-ids="chainIds"
      :edit-mode="modelValue.mode === 'edit'"
      @update:chain="selectChain($event)"
    />

    <ValidatorAccountForm
      v-if="modelValue.type === 'validator'"
      ref="form"
      v-model:error-messages="errors"
      :validator="modelValue.data"
      :edit-mode="modelValue.mode === 'edit'"
      :loading="loading"
      @update:validator="setValidator($event)"
    />

    <BtcAccountForm
      v-else-if="modelValue.type === 'xpub'"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errors"
      :loading="loading"
      @detected-address="startPromise(handleDetectedAddress($event))"
    />

    <AgnosticAddressAccountForm
      v-else-if="modelValue.type === 'group'"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errors"
      :loading="loading"
    />

    <AddressAccountForm
      v-else
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errors"
      :loading="loading"
      @detected-xpub="startPromise(handleDetectedXpub($event))"
    />
  </div>
</template>
