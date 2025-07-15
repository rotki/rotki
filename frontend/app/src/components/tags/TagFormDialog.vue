<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { Tag } from '@/types/tags';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import TagForm from '@/components/tags/TagForm.vue';
import { useTagStore } from '@/store/session/tags';

const modelValue = defineModel<Tag | undefined>({ required: true });

const props = withDefaults(
  defineProps<{
    editMode?: boolean;
  }>(),
  {
    editMode: false,
  },
);

const { addTag, editTag } = useTagStore();

const submitting = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const form = useTemplateRef<ComponentExposed<typeof TagForm>>('form');

const { t } = useI18n({ useScope: 'global' });

async function save() {
  const newTag = get(modelValue);
  if (!await get(form)?.validate() || !newTag) {
    return;
  }
  const status = await (props.editMode ? editTag(newTag) : addTag(newTag));

  if (status.success) {
    set(modelValue, undefined);
  }
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
    @cancel="modelValue = undefined"
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
