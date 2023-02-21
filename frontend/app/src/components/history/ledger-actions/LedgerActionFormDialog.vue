<script setup lang="ts">
import { type Ref } from 'vue';
import LedgerActionForm from '@/components/history/ledger-actions/LedgerActionForm.vue';
import { type LedgerActionEntry } from '@/types/history/ledger-action/ledger-actions';

withDefaults(
  defineProps<{
    open: boolean;
    edit?: boolean;
    formData?: Partial<LedgerActionEntry> | null;
    loading?: boolean;
  }>(),
  {
    edit: false,
    formData: null,
    loading: false
  }
);

const emit = defineEmits<{
  (e: 'update:open', open: boolean): void;
  (e: 'reset-edit'): void;
  (e: 'saved'): void;
}>();

const valid: Ref<boolean> = ref(false);
const form = ref<InstanceType<typeof LedgerActionForm> | null>(null);

const clearDialog = () => {
  get(form)?.reset();
  emit('update:open', false);
  emit('reset-edit');
};

const confirmSave = async () => {
  if (get(form)) {
    const success = await get(form)?.save();
    if (success) {
      clearDialog();
      emit('saved');
    }
  }
};

const { tc } = useI18n();
</script>
<template>
  <big-dialog
    :display="open"
    :title="
      edit
        ? tc('ledger_actions.dialog.edit.title')
        : tc('ledger_actions.dialog.add.title')
    "
    :subtitle="
      edit
        ? tc('ledger_actions.dialog.edit.subtitle')
        : tc('ledger_actions.dialog.add.subtitle')
    "
    :primary-action="tc('common.actions.save')"
    :action-disabled="loading || !valid"
    @confirm="confirmSave()"
    @cancel="clearDialog()"
  >
    <ledger-action-form
      ref="form"
      v-model="valid"
      :edit="edit"
      :form-data="formData"
    />
  </big-dialog>
</template>
