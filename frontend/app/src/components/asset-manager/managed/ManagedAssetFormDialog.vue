<script setup lang="ts">
import { type SupportedAsset } from '@rotki/common/lib/data';

const props = withDefaults(
  defineProps<{
    title: string;
    subtitle?: string;
    editableItem?: SupportedAsset | null;
  }>(),
  {
    subtitle: '',
    editableItem: null
  }
);

const { editableItem } = toRefs(props);
const { t } = useI18n();

const { openDialog, submitting, closeDialog, trySubmit } =
  useManagedAssetForm();
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="title"
    :subtitle="subtitle"
    :primary-action="t('common.actions.save')"
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="closeDialog()"
  >
    <ManagedAssetForm :editable-item="editableItem" />
  </BigDialog>
</template>
