<script setup lang="ts">
import CopyButton from '@/modules/shell/components/CopyButton.vue';

const { directory, isPackaged = false } = defineProps<{
  directory: string;
  isPackaged?: boolean;
}>();

const emit = defineEmits<{
  'open-path': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center justify-between gap-2">
    <RuiTooltip
      class="min-w-0"
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <div class="truncate">
          {{ directory }}
        </div>
      </template>
      <span class="max-w-70 break-all">
        {{ directory }}
      </span>
    </RuiTooltip>
    <div
      v-if="isPackaged"
      class="ml-2"
    >
      <RuiTooltip
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            icon
            size="sm"
            variant="text"
            @click="emit('open-path')"
          >
            <RuiIcon
              size="18"
              name="lu-folder-open"
            />
          </RuiButton>
        </template>
        <span>{{ t('about.open_data_dir_tooltip') }}</span>
      </RuiTooltip>
    </div>
    <div v-else>
      <CopyButton
        size="sm"
        :value="directory"
        :tooltip="t('about.copy_data_directory_tooltip')"
      />
    </div>
  </div>
</template>
