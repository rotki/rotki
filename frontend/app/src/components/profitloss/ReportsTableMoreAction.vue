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
  <RuiMenu
    menu-class="max-w-[15rem]"
    :popper="{ placement: 'bottom-end' }"
    close-on-content-click
  >
    <template #activator="{ attrs }">
      <RuiButton
        class="!p-2"
        icon
        variant="text"
        v-bind="attrs"
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
  </RuiMenu>
</template>
