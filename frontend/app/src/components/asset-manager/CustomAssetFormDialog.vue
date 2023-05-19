<script setup lang="ts">
import { type CustomAsset } from '@/types/asset';
import CustomAssetForm from '@/components/asset-manager/CustomAssetForm.vue';
import { useCustomAssetForm } from '@/composables/assets/forms/custom-asset-form';

const props = withDefaults(
  defineProps<{
    title: string;
    subtitle?: string;
    types?: string[];
    editableItem?: CustomAsset | null;
  }>(),
  {
    subtitle: '',
    types: () => [],
    editableItem: null
  }
);

const { editableItem } = toRefs(props);
const { t } = useI18n();

const { valid, openDialog, submitting, closeDialog, trySubmit } =
  useCustomAssetForm();
</script>

<template>
  <big-dialog
    :display="openDialog"
    :title="title"
    :subtitle="subtitle"
    :action-disabled="submitting || !valid"
    :primary-action="t('common.actions.save')"
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="closeDialog()"
  >
    <custom-asset-form :types="types" :edit="editableItem" />
  </big-dialog>
</template>
