<script lang="ts" setup>
import { type ComputedRef, type Ref } from 'vue';
import { type Trade } from '@/types/history/trade';
import ExternalTradeForm from '@/components/history/trades/ExternalTradeForm.vue';

const props = withDefaults(
  defineProps<{
    value: boolean;
    editableItem?: Trade | null;
    loading?: boolean;
  }>(),
  {
    editableItem: null
  }
);

const { editableItem } = toRefs(props);

const emit = defineEmits<{
  (e: 'input', open: boolean): void;
  (e: 'reset-edit'): void;
  (e: 'saved'): void;
}>();

const valid: Ref<boolean> = ref(false);
const form = ref<InstanceType<typeof ExternalTradeForm> | null>(null);

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

const title: ComputedRef<string> = computed(() => {
  return get(editableItem)
    ? tc('closed_trades.dialog.edit.title')
    : tc('closed_trades.dialog.add.title');
});

const subtitle: ComputedRef<string> = computed(() => {
  return get(editableItem) ? tc('closed_trades.dialog.edit.subtitle') : '';
});
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
    <external-trade-form ref="form" v-model="valid" :edit="editableItem" />
  </big-dialog>
</template>
