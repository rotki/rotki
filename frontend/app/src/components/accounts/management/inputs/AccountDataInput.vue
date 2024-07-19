<script setup lang="ts">
defineProps<{
  disabled: boolean;
}>();

const labelModel = defineModel<string>('label', { required: true });
const tagsModel = defineModel<string[]>('tags', { required: true });

const { t } = useI18n();
</script>

<template>
  <RuiTextField
    v-model="labelModel"
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
