<script lang="ts" setup>
import type { Trade } from '@/types/history/trade';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ExternalTradeForm from '@/components/history/trades/ExternalTradeForm.vue';
import { useTrades } from '@/composables/history/trades';
import { useMessageStore } from '@/store/message';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';

const modelValue = defineModel<Trade | undefined>({ required: true });

const props = defineProps<{
  editMode: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const { t } = useI18n();

const submitting = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof ExternalTradeForm>>('form');
const stateUpdated = ref(false);

const dialogTitle = computed<string>(() =>
  props.editMode ? t('closed_trades.dialog.edit.title') : t('closed_trades.dialog.add.title'),
);

const dialogSubtitle = computed<string>(() =>
  props.editMode ? t('closed_trades.dialog.edit.subtitle') : '',
);

const { setMessage } = useMessageStore();

const { addExternalTrade, editExternalTrade } = useTrades();

async function save(): Promise<boolean> {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const data = get(modelValue);
  const editMode = props.editMode;
  const payload = {
    ...data,
  };

  set(submitting, true);
  const result = !editMode
    ? await addExternalTrade(omit(payload, ['tradeId']))
    : await editExternalTrade(payload);

  if (!result.success && result.message) {
    if (typeof result.message === 'string') {
      setMessage({
        description: result.message,
      });
    }
    else {
      set(errorMessages, {
        ...get(errorMessages),
        ...result.message,
      });
      await formRef?.validate();
    }
  }

  set(submitting, false);
  if (result.success) {
    set(modelValue, undefined);
    emit('refresh');
  }
  return result.success;
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="dialogTitle"
    :subtitle="dialogSubtitle"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <ExternalTradeForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>
