<script setup lang="ts">
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';

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
  <SettingsItem :id="SettingsHighlightIds.ASSET_UPDATE">
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
