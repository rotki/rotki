<script setup lang="ts">
const props = defineProps<{
  label: string;
  tags: string[];
  disabled: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:label', label: string): void;
  (e: 'update:tags', tags: string[]): void;
}>();

const { t } = useI18n();

const labelModel = useVModel(props, 'label', emit);
const tagsModel = useVModel(props, 'tags', emit);
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
