<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

defineProps<{
  label: string;
  tags: string[];
  disabled: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:label', label: string): void;
  (e: 'update:tags', tags: string[]): void;
}>();

const { t } = useI18n();
</script>

<template>
  <fragment>
    <v-text-field
      :value="label"
      data-cy="account-label-field"
      outlined
      class="account-form__label"
      :label="t('common.name')"
      :disabled="disabled"
      @input="emit('update:label', $event || '')"
    />

    <tag-input
      :value="tags"
      data-cy="account-tag-field"
      outlined
      :disabled="disabled"
      @input="emit('update:tags', $event)"
    />
  </fragment>
</template>
