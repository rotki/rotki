<script setup lang="ts">
import { assert } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import AccountForm from '@/components/accounts/management/AccountForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { type AccountManageState, useAccountManage } from '@/composables/accounts/blockchain/use-account-manage';
import { useAccountLoading } from '@/composables/accounts/loading';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { useGeneralSettingsStore } from '@/store/settings/general';

const model = defineModel<AccountManageState | undefined>({ required: true });

defineProps<{
  chainIds: string[];
}>();

const emit = defineEmits<{
  (e: 'complete'): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const form = ref<InstanceType<typeof AccountForm>>();
const stateUpdated = ref(false);

const title = computed<string>(() =>
  get(model)?.mode === 'edit'
    ? t('blockchain_balances.form_dialog.edit_title')
    : t('blockchain_balances.form_dialog.add_title'),
);

const subtitle = computed<string>(() =>
  get(model)?.mode === 'edit' ? t('blockchain_balances.form_dialog.edit_subtitle') : '',
);

const { errorMessages, pending, save } = useAccountManage();
const { loading } = useAccountLoading();
const { apiKey } = useExternalApiKeys(t);
const { beaconRpcEndpoint } = storeToRefs(useGeneralSettingsStore());

const isSaveDisabled = computed<boolean>(() => {
  const state = get(model);
  if (!state || state.mode === 'edit')
    return false;

  // Disable save button for validator addition without beaconchain API key and consensus client RPC
  return state.type === 'validator' && !(get(apiKey('beaconchain')) || get(beaconRpcEndpoint));
});

function dismiss() {
  set(model, undefined);
}

async function confirm() {
  assert(isDefined(form));
  const accountForm = get(form);
  set(errorMessages, {});
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
  </BigDialog>
</template>
