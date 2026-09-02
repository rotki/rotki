<script setup lang="ts">
import CopyButton from '@/modules/shell/components/CopyButton.vue';

const { dataDirectory, isPackaged = false } = defineProps<{
  dataDirectory: string;
  isPackaged?: boolean;
}>();

const emit = defineEmits<{
  'open-path': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center justify-between">
    <RuiTooltip
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <div class="truncate text-rui-text-secondary max-w-[280px]">
          {{ dataDirectory }}
        </div>
      </template>
      <span class="max-w-[280px]">
        {{ dataDirectory }}
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
        :value="dataDirectory"
        :tooltip="t('about.copy_data_directory_tooltip')"
      />
    </div>
  </div>
</template>
