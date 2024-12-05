<script setup lang="ts">
import { useManagedAssetForm } from '@/composables/assets/forms/managed-asset-form';
import type { SupportedAsset } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    title: string;
    subtitle?: string;
    editableItem?: SupportedAsset | null;
  }>(),
  {
    editableItem: null,
    subtitle: '',
  },
);

const { editableItem } = toRefs(props);
const { t } = useI18n();

const { closeDialog, openDialog, stateUpdated, submitting, trySubmit } = useManagedAssetForm();
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
    <ManagedAssetForm :editable-item="editableItem" />
  </BigDialog>
</template>
