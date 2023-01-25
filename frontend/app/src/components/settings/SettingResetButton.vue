<script setup lang="ts">
const emit = defineEmits<{ (e: 'click'): void }>();
const { t } = useI18n();
</script>
<template>
  <div class="mt-n2">
    <v-tooltip top max-width="200">
      <template #activator="{ on, attrs }">
        <v-btn icon v-bind="attrs" v-on="on" @click="emit('click')">
          <v-icon>mdi-cog-counterclockwise</v-icon>
        </v-btn>
      </template>
      <span>{{ t('backend_settings.actions.reset') }}</span>
    </v-tooltip>
  </div>
</template>
