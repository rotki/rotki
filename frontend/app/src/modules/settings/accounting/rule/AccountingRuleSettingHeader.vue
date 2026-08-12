<script setup lang="ts">
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';

defineProps<{
  loading: boolean;
  exportLoading: boolean;
  importLoading: boolean;
  resetLoading: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
  add: [];
  export: [];
  import: [];
  reset: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="pb-5 border-b border-default flex flex-wrap gap-2 items-center justify-between">
    <SettingCategoryHeader>
      <template #title>
        {{ t('accounting_settings.rule.title') }}
      </template>
      <template #subtitle>
        {{ t('accounting_settings.rule.subtitle') }}
      </template>
    </SettingCategoryHeader>
    <div class="flex items-center justify-end gap-2">
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
            @click="emit('refresh')"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('accounting_settings.rule.refresh_tooltip') }}
      </RuiTooltip>
      <RuiButton
        color="primary"
        @click="emit('add')"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('accounting_settings.rule.add') }}
      </RuiButton>
      <RuiMenu
        :popper="{ placement: 'bottom-end' }"
        close-on-content-click
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="!p-2"
            v-bind="attrs"
          >
            <RuiIcon
              name="lu-ellipsis-vertical"
              size="20"
            />
          </RuiButton>
        </template>
        <RuiButton
          variant="list"
          :loading="exportLoading"
          @click="emit('export')"
        >
          <template #prepend>
            <RuiIcon name="lu-file-down" />
          </template>
          {{ t('accounting_settings.rule.export') }}
        </RuiButton>
        <RuiButton
          variant="list"
          :loading="importLoading"
          @click="emit('import')"
        >
          <template #prepend>
            <RuiIcon name="lu-file-up" />
          </template>
          {{ t('accounting_settings.rule.import') }}
        </RuiButton>
        <RuiButton
          variant="list"
          :loading="resetLoading"
          @click="emit('reset')"
        >
          <template #prepend>
            <RuiIcon name="lu-history" />
          </template>
          {{ t('accounting_settings.rule.reset') }}
        </RuiButton>
      </RuiMenu>
    </div>
  </div>
</template>
