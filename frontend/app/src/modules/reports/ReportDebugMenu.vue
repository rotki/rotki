<script setup lang="ts">
const emit = defineEmits<{
  'export-data': [];
  'import-data': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiMenu
    close-on-content-click
    :options="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="outlined"
        size="xl"
        v-bind="attrs"
      >
        <template #prepend>
          <RuiIcon name="lu-bug" />
        </template>
        {{ t('profit_loss_reports.debug.title') }}
      </RuiButton>
    </template>
    <RuiButton
      variant="list"
      @click="emit('export-data')"
    >
      <template #prepend>
        <RuiIcon name="lu-file-down" />
      </template>
      {{ t('profit_loss_reports.debug.export_data') }}
    </RuiButton>
    <RuiButton
      variant="list"
      @click="emit('import-data')"
    >
      <template #prepend>
        <RuiIcon name="lu-file-up" />
      </template>
      {{ t('profit_loss_reports.debug.import_data') }}
    </RuiButton>
  </RuiMenu>
</template>
