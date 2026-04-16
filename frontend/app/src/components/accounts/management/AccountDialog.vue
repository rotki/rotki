<script setup lang="ts">
import { assert } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { isEqual } from 'es-toolkit';
import AccountForm from '@/components/accounts/management/AccountForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { type AccountManageState, useAccountManage } from '@/composables/accounts/blockchain/use-account-manage';
import { useAccountLoading } from '@/composables/accounts/loading';
import { usePremiumHelper } from '@/composables/premium';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const model = defineModel<AccountManageState | undefined>({ required: true });

defineProps<{
  chainIds: string[];
}>();

const emit = defineEmits<{
  complete: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const form = useTemplateRef<InstanceType<typeof AccountForm>>('form');
const stateUpdated = ref(false);

const title = computed<string>(() =>
  get(model)?.mode === 'edit'
    ? t('blockchain_balances.form_dialog.edit_title')
    : t('blockchain_balances.form_dialog.add_title'),
);

const subtitle = computed<string>(() =>
  get(model)?.mode === 'edit' ? t('blockchain_balances.form_dialog.edit_subtitle') : '',
);

const { errorMessages, pending, save, saveError, saveErrorIsPremium } = useAccountManage();
const { loading } = useAccountLoading();
const { getApiKey } = useExternalApiKeys();
const { beaconRpcEndpoint } = storeToRefs(useGeneralSettingsStore());
const { validatorsLimitInfo } = useEthStaking();
const { currentTier, ethStakedLimit, premium } = usePremiumHelper();

const isValidatorLimitReached = computed<boolean>(() => {
  const state = get(model);
  if (!state || state.mode === 'edit')
    return false;

  return state.type === 'validator' && get(validatorsLimitInfo).showWarning;
});

const upgradeLinkText = computed<string>(() =>
  get(premium)
    ? t('upgrade_row.upgrade_your_plan')
    : t('upgrade_row.rotki_premium'),
);

const upgradeLinkUrl = computed<string | undefined>(() =>
  get(premium) ? externalLinks.manageSubscriptions : undefined,
);

const isSaveDisabled = computed<boolean>(() => {
  const state = get(model);
  if (!state || state.mode === 'edit')
    return false;

  if (get(isValidatorLimitReached))
    return true;

  // Disable save button for validator addition without beaconchain API key and consensus client RPC
  return state.type === 'validator' && !(getApiKey('beaconchain') || get(beaconRpcEndpoint));
});

function dismiss() {
  set(saveError, '');
  set(saveErrorIsPremium, false);
  set(model, undefined);
}

async function confirm() {
  assert(isDefined(form));
  const accountForm = get(form);
  set(errorMessages, {});
  set(saveError, '');
  const valid = await accountForm.validate();
  if (!valid)
    return;

  const state = get(model);
  assert(state);

  set(stateUpdated, false);
  const success = await save(state);
  if (success) {
    emit('complete');
    dismiss();
  }
  else {
    set(stateUpdated, true);
  }
}
watch(model, (model, oldModel) => {
  if (!model || !oldModel) {
    set(stateUpdated, false);
    return;
  }

  if (model.chain === oldModel.chain && !isEqual(model.data, oldModel.data)) {
    set(stateUpdated, true);
  }
}, { deep: true });
</script>

<template>
  <BigDialog
    :display="!!model"
    :title="title"
    :subtitle="subtitle"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :loading="loading || pending"
    :action-disabled="isSaveDisabled"
    :prompt-on-close="stateUpdated"
    @confirm="confirm()"
    @cancel="dismiss()"
  >
    <AccountForm
      v-if="model"
      ref="form"
      v-model="model"
      v-model:error-messages="errorMessages"
      :chain-ids="chainIds"
      :loading="loading"
    />

    <RuiAlert
      v-if="saveError"
      type="error"
      class="mt-4"
    >
      <template v-if="saveErrorIsPremium">
        <i18n-t
          scope="global"
          keypath="blockchain_balances.eth_staking_limit_error"
          tag="span"
        >
          <template #limit>
            {{ ethStakedLimit }}
          </template>
          <template #currentTier>
            {{ currentTier }}
          </template>
          <template #link>
            <ExternalLink
              :text="upgradeLinkText"
              :url="upgradeLinkUrl"
              premium
              color="primary"
            />
          </template>
        </i18n-t>
      </template>
      <template v-else>
        {{ saveError }}
      </template>
    </RuiAlert>

    <RuiAlert
      v-if="isValidatorLimitReached"
      type="error"
      class="mt-4"
    >
      <i18n-t
        scope="global"
        keypath="blockchain_balances.validator_limit_reached"
        tag="span"
      >
        <template #limit>
          {{ validatorsLimitInfo.limit }}
        </template>
        <template #total>
          {{ validatorsLimitInfo.total }}
        </template>
        <template #link>
          <ExternalLink
            :text="upgradeLinkText"
            :url="upgradeLinkUrl"
            premium
            color="primary"
          />
        </template>
      </i18n-t>
    </RuiAlert>
  </BigDialog>
</template>
