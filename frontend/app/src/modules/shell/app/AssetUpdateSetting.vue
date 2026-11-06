<script setup lang="ts">
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';

const { upToDate = false } = defineProps<{
  skipped: number;
  loading: boolean;
  /** Whether the last check found nothing newer, said beside the button that ran it. */
  upToDate?: boolean;
}>();

const emit = defineEmits<{
  check: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsItem action-key="assetUpdate">
    <template #title>
      {{ t('asset_update.manual.title') }}
    </template>
    <template #subtitle>
      {{ t('asset_update.manual.subtitle') }}
    </template>
    <div class="flex flex-wrap items-center gap-4">
      <RuiButton
        variant="outlined"
        color="primary"
        :loading="loading"
        @click="emit('check')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-refresh-ccw"
            size="16"
          />
        </template>
        {{ t('asset_update.manual.check') }}
      </RuiButton>
      <span
        v-if="upToDate"
        class="text-sm text-rui-success"
        role="status"
        data-testid="asset-update-up-to-date"
      >
        {{ t('asset_update.up_to_date') }}
      </span>
      <i18n-t
        v-if="skipped"
        scope="global"
        keypath="asset_update.manual.skipped"
        tag="div"
        class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-rui-text-secondary"
      >
        <template #skipped>
          <BadgeDisplay>
            {{ skipped }}
          </BadgeDisplay>
        </template>
      </i18n-t>
    </div>
  </SettingsItem>
</template>
