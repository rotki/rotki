<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { Tag } from '@/modules/tags/tags';
import { tap } from 'plainfp/result';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import { useFailureSlot } from '@/modules/shell/components/named-failure';
import TagForm from '@/modules/tags/TagForm.vue';
import { useTagOperations } from '@/modules/tags/use-tag-operations';

const modelValue = defineModel<Tag | undefined>({ required: true });

const { editMode = false, originalName = '' } = defineProps<{
  editMode?: boolean;
  originalName?: string;
}>();

const emit = defineEmits<{
  saved: [{ tag: Tag; originalName: string }];
}>();

const { addTag, editTag } = useTagOperations();
/** Why the last save failed; the form keeps what was typed. */
const { clear: clearSaveFailure, failure: saveFailure, run: runSave } = useFailureSlot();

const submitting = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const form = useTemplateRef<ComponentExposed<typeof TagForm>>('form');

const { t } = useI18n({ useScope: 'global' });

function closeDialog(): void {
  clearSaveFailure();
  set(stateUpdated, false);
  set(modelValue, undefined);
}

async function save(): Promise<void> {
  set(submitting, true);
  clearSaveFailure();
  const newTag = get(modelValue);
  if (!get(form)?.validate() || !newTag) {
    set(submitting, false);
    return;
  }
  const tagOriginalName = originalName || newTag.name;
  await runSave(
    editMode ? t('actions.session.tag_edit.error.title') : t('actions.session.tag_add.error.title'),
    async () => tap(await (editMode ? editTag(newTag, tagOriginalName) : addTag(newTag)), () => {
      emit('saved', { tag: newTag, originalName: tagOriginalName });
      closeDialog();
    }),
  );
  set(submitting, false);
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="editMode ? t('tag_manager.edit_tag.title') : t('tag_manager.create_tag.title')"
    :subtitle="editMode ? t('tag_manager.edit_tag.subtitle') : t('tag_manager.create_tag.subtitle')"
    :action="{ primary: t('common.actions.save') }"
    :layout="{ divide: true }"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    :failure="saveFailure?.failure"
    :failure-title="saveFailure?.title"
    @confirm="save()"
    @cancel="closeDialog()"
  >
    <TagForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:state-updated="stateUpdated"
    />
  </BigDialog>
</template>
