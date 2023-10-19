<script setup lang="ts">
import { type Ref } from 'vue';
import { RefreshableCache } from '@/types/session/purge';

const { t } = useI18n();

const refreshable = [
  {
    id: RefreshableCache.GENERAL_CACHE,
    text: t('data_management.refresh_cache.label.general_cache')
  }
];

const source: Ref<RefreshableCache> = ref(RefreshableCache.GENERAL_CACHE);

const { refreshGeneralCache } = useSessionPurge();

const refreshSource = async (source: RefreshableCache) => {
  if (source === RefreshableCache.GENERAL_CACHE) {
    await refreshGeneralCache();
  }
};

const { status, pending, showConfirmation } = useCacheClear<RefreshableCache>(
  refreshable,
  refreshSource,
  (source: string) => ({
    success: t('data_management.refresh_cache.success', {
      source
    }),
    error: t('data_management.refresh_cache.error', {
      source
    })
  }),
  (source: string) => ({
    title: t('data_management.refresh_cache.confirm.title'),
    message: t('data_management.refresh_cache.confirm.message', {
      source
    })
  })
);
</script>

<template>
  <div class="mb-2">
    <div class="mb-6">
      <div class="text-h6">
        {{ t('data_management.refresh_cache.title') }}
      </div>
      <div>
        {{ t('data_management.refresh_cache.subtitle') }}
      </div>
    </div>

    <div class="flex items-center gap-4">
      <VAutocomplete
        v-model="source"
        class="flex-1"
        outlined
        :label="t('data_management.refresh_cache.select_cache')"
        :items="refreshable"
        item-text="text"
        item-value="id"
        hide-details
        :disabled="pending"
      />

      <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
        <template #activator>
          <RuiButton
            variant="text"
            icon
            :disabled="!source || pending"
            :loading="pending"
            @click="showConfirmation(source)"
          >
            <RuiIcon name="restart-line" />
          </RuiButton>
        </template>
        <span> {{ t('data_management.refresh_cache.tooltip') }} </span>
      </RuiTooltip>
    </div>

    <ActionStatusIndicator v-if="status" :status="status" />
  </div>
</template>
