<script setup lang="ts">
const emit = defineEmits<{ (e: 'click'): void }>();
const { t } = useI18n();
</script>

<template>
  <div class="mt-n2">
    <VTooltip top max-width="200">
      <template #activator="{ on, attrs }">
        <RuiButton
          icon
          variant="text"
          v-bind="attrs"
          v-on="on"
          @click="emit('click')"
        >
          <VIcon>mdi-cog-counterclockwise</VIcon>
        </RuiButton>
      </template>
      <span>{{ t('backend_settings.actions.reset') }}</span>
    </VTooltip>
  </div>
</template>
