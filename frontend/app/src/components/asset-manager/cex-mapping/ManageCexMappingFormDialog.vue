<script setup lang="ts">
import type { CexMapping } from '@/types/asset';

const props = withDefaults(
  defineProps<{
    title: string;
    subtitle?: string;
    editableItem?: CexMapping | null;
    selectedLocation?: string;
  }>(),
  {
    subtitle: '',
    editableItem: null,
    selectedLocation: undefined,
  },
);

const { editableItem } = toRefs(props);
const { t } = useI18n();

const { openDialog, submitting, closeDialog, trySubmit }
  = useCexMappingForm();
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
    <ManageCexMappingForm
      :editable-item="editableItem"
      :selected-location="selectedLocation"
    />
  </BigDialog>
</template>
