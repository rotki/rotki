<script setup lang="ts">
import type { CexMapping } from '@/types/asset';

const props = withDefaults(
  defineProps<{
    title: string;
    subtitle?: string;
    editMode?: boolean;
    form?: Partial<CexMapping> | null;
    selectedLocation?: string;
  }>(),
  {
    subtitle: '',
    editMode: false,
    form: null,
    selectedLocation: undefined,
  },
);

const { form } = toRefs(props);
const { t } = useI18n();

const { openDialog, submitting, closeDialog, trySubmit } = useCexMappingForm();
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
      :edit-mode="editMode"
      :form="form"
      :selected-location="selectedLocation"
    />
  </BigDialog>
</template>
