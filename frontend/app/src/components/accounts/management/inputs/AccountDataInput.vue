<script setup lang="ts">
import TagInput from '@/components/inputs/TagInput.vue';

const labelModel = defineModel<string>('label', { required: true });

const tagsModel = defineModel<string[]>('tags', { required: true });

defineProps<{
  disabled: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTextField
    v-model="labelModel"
    clearable
    data-cy="account-label-field"
    color="primary"
    variant="outlined"
    class="account-form__label"
    :label="t('common.name')"
    :disabled="disabled"
  />

  <TagInput
    v-model="tagsModel"
    data-cy="account-tag-field"
    :disabled="disabled"
  />
</template>
