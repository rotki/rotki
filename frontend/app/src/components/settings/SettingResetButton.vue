<script setup lang="ts">
const emit = defineEmits<{ (e: 'click'): void }>();
const { t } = useI18n();
</script>

<template>
  <div class="mt-n2">
    <VTooltip top max-width="200">
      <template #activator="{ on, attrs }">
        <VBtn icon v-bind="attrs" v-on="on" @click="emit('click')">
          <VIcon>mdi-cog-counterclockwise</VIcon>
        </VBtn>
      </template>
      <span>{{ t('backend_settings.actions.reset') }}</span>
    </VTooltip>
  </div>
</template>
