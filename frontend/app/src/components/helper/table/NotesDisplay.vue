<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

withDefaults(
  defineProps<{
    notes?: string | null;
  }>(),
  {
    notes: null
  }
);

const { t } = useI18n();
</script>

<template>
  <Fragment>
    <VRow>
      <VCol class="text-subtitle-2">
        {{ t('notes_display.notes') }}
      </VCol>
    </VRow>
    <VRow>
      <VCol>
        <Card outlined>
          {{ notes ? notes : t('notes_display.empty_notes') }}
        </Card>
      </VCol>
    </VRow>
  </Fragment>
</template>
