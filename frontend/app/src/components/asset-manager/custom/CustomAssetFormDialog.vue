<script setup lang="ts">
import { useCustomAssetForm } from '@/composables/assets/forms/custom-asset-form';
import CustomAssetForm from '@/components/asset-manager/custom/CustomAssetForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import type { CustomAsset } from '@/types/asset';

const props = withDefaults(
  defineProps<{
    title: string;
    subtitle?: string;
    types?: string[];
    editableItem?: CustomAsset | null;
  }>(),
  {
    editableItem: null,
    subtitle: '',
    types: () => [],
  },
);

const { editableItem } = toRefs(props);
const { t } = useI18n();

const { closeDialog, openDialog, stateUpdated, submitting, trySubmit } = useCustomAssetForm();
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="title"
    :subtitle="subtitle"
    :primary-action="t('common.actions.save')"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="trySubmit()"
    @cancel="closeDialog()"
  >
    <CustomAssetForm
      :types="types"
      :editable-item="editableItem"
    />
  </BigDialog>
</template>
