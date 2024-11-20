<script setup lang="ts">
import type { CustomAsset } from '@/types/asset';

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
    editableItem: null,
  },
);

const { editableItem } = toRefs(props);
const { t } = useI18n();

const { openDialog, submitting, closeDialog, trySubmit, stateUpdated } = useCustomAssetForm();
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
