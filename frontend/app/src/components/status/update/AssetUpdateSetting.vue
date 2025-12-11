<script setup lang="ts">
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';

defineProps<{
  skipped: number;
  loading: boolean;
}>();

const emit = defineEmits<{
  check: [];
}>();
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('asset_update.manual.title') }}
    </template>
    <template #subtitle>
      {{ t('asset_update.manual.subtitle') }}
    </template>
    <div class="flex items-center gap-4 justify-end">
      <i18n-t
        v-if="skipped"
        scope="global"
        keypath="asset_update.manual.skipped"
        tag="div"
        class="flex flex-wrap gap-x-2 gap-y-1"
      >
        <template #skipped>
          <BadgeDisplay>
            {{ skipped }}
          </BadgeDisplay>
        </template>
      </i18n-t>
      <RuiButton
        color="primary"
        :loading="loading"
        @click="emit('check')"
      >
        {{ t('asset_update.manual.check') }}
      </RuiButton>
    </div>
  </SettingsItem>
</template>
