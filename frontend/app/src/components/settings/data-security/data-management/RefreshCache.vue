<script setup lang="ts">
import { RefreshableCache } from '@/types/session/purge';

const { t } = useI18n();

const refreshable = [
  {
    id: RefreshableCache.GENERAL_CACHE,
    text: t('data_management.refresh_cache.label.general_cache'),
  },
];

const source: Ref<RefreshableCache> = ref(RefreshableCache.GENERAL_CACHE);

const { refreshGeneralCache } = useSessionPurge();

async function refreshSource(source: RefreshableCache) {
  if (source === RefreshableCache.GENERAL_CACHE)
    await refreshGeneralCache();
}

const { status, pending, showConfirmation } = useCacheClear<RefreshableCache>(
  refreshable,
  refreshSource,
  (source: string) => ({
    success: t('data_management.refresh_cache.success', {
      source,
    }),
    error: t('data_management.refresh_cache.error', {
      source,
    }),
  }),
  (source: string) => ({
    title: t('data_management.refresh_cache.confirm.title'),
    message: t('data_management.refresh_cache.confirm.message', {
      source,
    }),
  }),
);
</script>

<template>
  <div>
    <RuiCardHeader class="p-0 mb-4">
      <template #header>
        {{ t('data_management.refresh_cache.title') }}
      </template>
      <template #subheader>
        {{ t('data_management.refresh_cache.subtitle') }}
      </template>
    </RuiCardHeader>

    <div class="flex items-center gap-4">
      <RuiAutoComplete
        v-model="source"
        class="flex-1"
        variant="outlined"
        :label="t('data_management.refresh_cache.select_cache')"
        :options="refreshable"
        text-attr="text"
        key-attr="id"
        :disabled="pending"
      />

      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        class="-mt-6"
      >
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

    <ActionStatusIndicator
      v-if="status"
      class="mt-4"
      :status="status"
    />
  </div>
</template>
