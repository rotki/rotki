<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import { type LedgerActionEntry } from '@/types/history/ledger-action/ledger-actions';
import LedgerActionForm from '@/components/history/ledger-actions/LedgerActionForm.vue';

const props = withDefaults(
  defineProps<{
    value: boolean;
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

const { edit } = toRefs(props);

const emit = defineEmits<{
  (e: 'input', open: boolean): void;
  (e: 'reset-edit'): void;
  (e: 'saved'): void;
}>();

const valid: Ref<boolean> = ref(false);
const form = ref<InstanceType<typeof LedgerActionForm> | null>(null);

const clearDialog = () => {
  get(form)?.reset();
  emit('input', false);
  emit('reset-edit');
};

const confirmSave = async () => {
  if (!isDefined(form)) {
    return;
  }
  const success = await get(form)?.save();
  if (success) {
    clearDialog();
    emit('saved');
  }
};

const { tc } = useI18n();

const title: ComputedRef<string> = computed(() =>
  get(edit)
    ? tc('ledger_actions.dialog.edit.title')
    : tc('ledger_actions.dialog.add.title')
);

const subtitle: ComputedRef<string> = computed(() =>
  get(edit)
    ? tc('ledger_actions.dialog.edit.subtitle')
    : tc('ledger_actions.dialog.add.subtitle')
);
</script>
<template>
  <big-dialog
    :display="value"
    :title="title"
    :subtitle="subtitle"
    :primary-action="tc('common.actions.save')"
    :action-disabled="loading || !valid"
    :loading="loading"
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
