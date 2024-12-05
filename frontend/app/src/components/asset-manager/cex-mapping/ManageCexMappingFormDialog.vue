<script setup lang="ts">
import { useCexMappingForm } from '@/composables/assets/forms/cex-mapping-form';
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
    editMode: false,
    form: null,
    selectedLocation: undefined,
    subtitle: '',
  },
);

const { form } = toRefs(props);
const { t } = useI18n();

const { closeDialog, openDialog, stateUpdated, submitting, trySubmit } = useCexMappingForm();
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
    <ManageCexMappingForm
      :edit-mode="editMode"
      :form="form"
      :selected-location="selectedLocation"
    />
  </BigDialog>
</template>
