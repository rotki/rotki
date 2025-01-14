<script setup lang="ts">
import { useTemplateRef } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import WrappedContainer from '@/components/wrapped/WrappedContainer.vue';

const display = defineModel<boolean>('display', { required: true });

const { t } = useI18n();

const container = useTemplateRef<InstanceType<typeof WrappedContainer>>('container');

const highlightedYear = 2024;

function closeDialog() {
  set(display, false);
}
</script>

<template>
  <BigDialog
    :display="display"
    :title="t('wrapped.title', { year: container?.isHighlightedYear ? highlightedYear : undefined })"
    :subtitle="t('wrapped.subtitle')"
    :loading="container?.loading"
    :action-hidden="true"
    :secondary-action="t('common.actions.close')"
    max-width="800px"
    @cancel="closeDialog()"
    @close="closeDialog()"
  >
    <WrappedContainer
      v-if="display"
      ref="container"
      :highlighted-year="highlightedYear"
    />
  </BigDialog>
</template>
