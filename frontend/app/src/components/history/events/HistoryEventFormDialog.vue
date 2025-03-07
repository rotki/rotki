<script lang="ts" setup>
import type { HistoryEvent, HistoryEventEntry } from '@/types/history/events';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import HistoryEventForm from '@/components/history/events/HistoryEventForm.vue';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { useTemplateRef } from 'vue';

const open = defineModel<boolean>('open', { required: true });

const props = withDefaults(
  defineProps<{
    editableItem?: HistoryEventEntry;
    nextSequence?: string;
    loading?: boolean;
    groupHeader?: HistoryEvent;
    groupEvents?: HistoryEvent[];
  }>(),
  {
    editableItem: undefined,
    groupEvents: undefined,
    groupHeader: undefined,
    loading: false,
    nextSequence: undefined,
  },
);

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const { editableItem, groupHeader } = toRefs(props);

const { defaultNotes } = useHistoryEventsForm();

const { t } = useI18n();

const stateUpdated = ref<boolean>(false);
const loading = ref<boolean>(false);
const form = useTemplateRef<InstanceType<typeof HistoryEventForm>>('form');

const title = computed<string>(() =>
  get(editableItem)
    ? t('transactions.events.dialog.edit.title')
    : t('transactions.events.dialog.add.title'),
);

watchImmediate(editableItem, (editable) => {
  set(defaultNotes, editable?.defaultNotes);
});

async function save() {
  set(loading, true);
  const success = await get(form)?.save();
  set(loading, false);

  if (success) {
    set(open, false);
    emit('refresh');
  }
}
</script>

<template>
  <BigDialog
    :display="open"
    :title="title"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="open = false"
  >
    <HistoryEventForm
      ref="form"
      v-model:state-updated="stateUpdated"
      :group-header="groupHeader"
      :editable-item="editableItem"
      :next-sequence="nextSequence"
      :default-notes="defaultNotes"
      :group-events="groupEvents"
    />
  </BigDialog>
</template>
