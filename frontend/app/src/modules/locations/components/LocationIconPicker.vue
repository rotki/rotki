<script setup lang="ts">
import { LOCATION_ICONS, type LocationIcon } from '@/modules/locations/location-icons';

const model = defineModel<LocationIcon>({ required: true });

const { t } = useI18n({ useScope: 'global' });

/** The icon's name as a reader says it, `lu-piggy-bank` being "piggy bank". */
function spokenName(icon: LocationIcon): string {
  return icon.replace(/^lu-/, '').replaceAll('-', ' ');
}
</script>

<template>
  <div
    class="flex flex-col gap-2"
    data-testid="location-icon-picker"
  >
    <span class="text-body-2 text-rui-text-secondary">{{ t('location_manager.form.icon') }}</span>
    <div class="grid grid-cols-10 gap-1 w-max">
      <RuiButton
        v-for="icon in LOCATION_ICONS"
        :key="icon"
        :variant="model === icon ? 'default' : 'text'"
        :color="model === icon ? 'primary' : undefined"
        icon
        size="sm"
        :title="t('location_manager.form.icon_option', { icon: spokenName(icon) })"
        :aria-label="t('location_manager.form.icon_option', { icon: spokenName(icon) })"
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
