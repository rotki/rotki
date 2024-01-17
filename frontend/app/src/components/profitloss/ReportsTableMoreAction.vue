<script setup lang="ts">
defineProps<{
  showExportButton: boolean;
}>();

const emit = defineEmits<{
  (e: 'delete'): void;
}>();

const { t } = useI18n();
</script>

<template>
  <VMenu
    max-width="250px"
    min-width="200px"
    left
    offset-y
    transition="slide-y-transition"
  >
    <template #activator="{ on }">
      <RuiButton
        class="!p-2"
        icon
        variant="text"
        v-on="on"
      >
        <RuiIcon
          name="more-2-fill"
          size="20"
        />
      </RuiButton>
    </template>
    <div class="py-2">
      <ExportReportCsv
        v-if="showExportButton"
        list
      />
      <RuiButton
        variant="list"
        color="error"
        @click="emit('delete')"
      >
        <template #prepend>
          <RuiIcon
            size="20"
            name="delete-bin-5-line"
          />
        </template>

        {{ t('reports_table.delete') }}
      </RuiButton>
    </div>
  </VMenu>
</template>
