<script setup lang="ts">
import { LOCATION_ICONS, type LocationIcon } from '@/modules/locations/location-icons';

const model = defineModel<LocationIcon>({ required: true });

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    class="flex flex-col gap-2"
    data-testid="location-icon-picker"
  >
    <span class="text-body-2 text-rui-text-secondary">{{ t('location_manager.form.icon') }}</span>
    <div class="flex flex-wrap gap-1">
      <RuiButton
        v-for="icon in LOCATION_ICONS"
        :key="icon"
        :variant="model === icon ? 'default' : 'text'"
        :color="model === icon ? 'primary' : undefined"
        icon
        size="sm"
        :data-testid="`location-icon-${icon}`"
        :aria-pressed="model === icon"
        @click="model = icon"
      >
        <RuiIcon
          :name="icon"
          size="20"
        />
      </RuiButton>
    </div>
  </div>
</template>
