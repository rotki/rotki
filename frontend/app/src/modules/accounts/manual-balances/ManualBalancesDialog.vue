<script setup lang="ts">
import type { ManualBalance, RawManualBalance } from '@/modules/balances/types/manual-balances';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { startPromise } from '@shared/utils';
import { useTemplateRef } from 'vue';
import ManualBalancesForm from '@/modules/accounts/manual-balances/ManualBalancesForm.vue';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<ManualBalance | RawManualBalance | undefined>({ required: true });

const emit = defineEmits<{
  'update-tab': [tab: string | number];
}>();

const { t } = useI18n({ useScope: 'global' });

const loading = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof ManualBalancesForm>>('form');
const stateUpdated = ref(false);

const { setMessage } = useMessageStore();
const { save: saveBalance } = useManualBalances();

const { refreshPrice, refreshPrices } = usePriceRefresh();

const isEdit = computed<boolean>(() => isDefined(modelValue) && 'identifier' in get(modelValue));

const dialogTitle = computed<string>(() => {
  if (get(isEdit))
    return t('manual_balances.dialog.edit.title');
  return t('manual_balances.dialog.add.title');
});

const dialogSubtitle = computed<string>(() => {
  if (get(isEdit))
    return t('manual_balances.dialog.edit.subtitle');
  return '';
});

type ManualBalanceForm = InstanceType<typeof ManualBalancesForm> | null | undefined;

/** Newly saved manual prices affect the displayed value, so both caches are refreshed. */
async function refreshSavedPrices(formRef: ManualBalanceForm, asset: string): Promise<void> {
  const newPricesSaved = await formRef?.savePrice();
  if (!newPricesSaved)
    return;

  startPromise(refreshPrice(asset));
  startPromise(refreshPrices());
}

/** A balance without an identifier is new, so the list switches to the tab it landed on. */
function notifyTabChange(payload: ManualBalance | RawManualBalance): void {
  if ('identifier' in payload)
    return;

  emit('update-tab', payload.balanceType === 'asset' ? 'assets' : 'liabilities');
}

/**
 * Field-level errors go back to the form so it can mark the offending inputs; a plain string has no
 * field to attach to and is surfaced as a message instead.
 */
function reportSaveFailure(message: string | ValidationErrors, formRef: ManualBalanceForm): void {
  if (typeof message !== 'string') {
    set(errorMessages, message);
    // The form renders the errors as they arrive; this only reveals the fields the user has not
    // touched yet, so a rejected save marks every offending input rather than the visited ones.
    formRef?.validate();
    return;
  }

  const obj = { message };
  setMessage({
    description: get(isEdit)
      ? t('actions.manual_balances.edit.error.description', obj)
      : t('actions.manual_balances.add.error.description', obj),
  });
}

async function save(): Promise<boolean> {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = formRef?.validate();
  if (!valid)
    return false;

  set(loading, true);
  await refreshSavedPrices(formRef, get(modelValue).asset);

  const payload = get(modelValue);
  const status = await saveBalance(payload);

  if (status.success) {
    set(modelValue, undefined);
    set(loading, false);
    notifyTabChange(payload);
    return true;
  }

  if (status.message)
    reportSaveFailure(status.message, formRef);

  set(loading, false);
  return false;
}
</script>

<template>
  <BigDialog
    v-if="modelValue"
    :display="!!modelValue"
    :title="dialogTitle"
    :subtitle="dialogSubtitle"
    :loading="loading"
    :action="{ primary: t('common.actions.save') }"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <ManualBalancesForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :submitting="loading"
    />
  </BigDialog>
</template>
