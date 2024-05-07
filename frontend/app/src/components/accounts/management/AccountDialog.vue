<script setup lang="ts">
import type AccountForm from '@/components/accounts/management/AccountForm.vue';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';

const props = defineProps<{
  value: AccountManageState | undefined;
}>();

const emit = defineEmits<{
  (e: 'input', value: AccountManageState | undefined): void;
}>();

const { t } = useI18n();

const form = ref<InstanceType<typeof AccountForm>>();

const model = useSimpleVModel(props, emit);

const title = computed<string>(() => props.value?.mode === 'edit'
  ? t('blockchain_balances.form_dialog.edit_title')
  : t('blockchain_balances.form_dialog.add_title'));

const subtitle = computed<string>(() => props.value?.mode === 'edit'
  ? t('blockchain_balances.form_dialog.edit_subtitle')
  : '');

const { save, pending, errorMessages } = useAccountManage();
const { loading } = useAccountLoading();

function dismiss() {
  set(model, undefined);
}

async function confirm() {
  assert(isDefined(form));
  const accountForm = get(form);
  const valid = await accountForm.validate();
  if (!valid)
    return;

  const importState = await accountForm.importAccounts();

  if (importState === null)
    return;

  const state = importState || get(model);
  assert(state);

  const success = await save(state);
  if (success)
    dismiss();
}
</script>

<template>
  <BigDialog
    :display="!!model"
    :title="title"
    :subtitle="subtitle"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :loading="loading || pending"
    @confirm="confirm()"
    @cancel="dismiss()"
  >
    <AccountForm
      v-if="model"
      ref="form"
      v-model="model"
      :error-messages.sync="errorMessages"
      :loading="loading"
    />
  </BigDialog>
</template>
