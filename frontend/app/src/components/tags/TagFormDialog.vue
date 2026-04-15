<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { Tag } from '@/modules/tags/tags';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import TagForm from '@/components/tags/TagForm.vue';
import { useTagOperations } from '@/modules/session/use-tag-operations';

const modelValue = defineModel<Tag | undefined>({ required: true });

const { editMode = false, originalName = '' } = defineProps<{
  editMode?: boolean;
  originalName?: string;
}>();

const emit = defineEmits<{
  saved: [{ tag: Tag; originalName: string }];
}>();

const { addTag, editTag } = useTagOperations();

const submitting = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const form = useTemplateRef<ComponentExposed<typeof TagForm>>('form');

const { t } = useI18n({ useScope: 'global' });

function closeDialog(): void {
  set(stateUpdated, false);
  set(modelValue, undefined);
}

async function save() {
  set(submitting, true);
  const newTag = get(modelValue);
  if (!await get(form)?.validate() || !newTag) {
    set(submitting, false);
    return;
  }
  const tagOriginalName = originalName || newTag.name;
  const status = await (editMode ? editTag(newTag, tagOriginalName) : addTag(newTag));

  if (status.success) {
    emit('saved', { tag: newTag, originalName: tagOriginalName });
    closeDialog();
  }
  set(submitting, false);
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="editMode ? t('tag_manager.edit_tag.title') : t('tag_manager.create_tag.title')"
    :subtitle="editMode ? t('tag_manager.edit_tag.subtitle') : t('tag_manager.create_tag.subtitle')"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    divide
    @confirm="save()"
    @cancel="closeDialog()"
  >
    <TagForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:state-updated="stateUpdated"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>
