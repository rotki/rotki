<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';
import ConfirmMenu from '@/modules/shell/components/ConfirmMenu.vue';

defineProps<{
  exportLoading: boolean;
  importLoading: boolean;
  resetLoading: boolean;
}>();

const emit = defineEmits<{
  add: [];
  export: [];
  import: [];
  reset: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const resetQuestion = computed<ConfirmQuestion>(() => ({
  confirmLabel: t('accounting_settings.rule.reset'),
  message: t('accounting_settings.rule.confirm_reset'),
  tone: 'error',
}));
</script>

<template>
  <div class="pb-3 border-b border-rui-divider flex flex-wrap gap-2 items-center justify-between">
    <SettingCategoryHeader>
      <template #title>
        {{ t('accounting_settings.rule.title') }}
      </template>
    </SettingCategoryHeader>
    <div class="flex items-center gap-1">
      <RuiButton
        color="primary"
        size="sm"
        data-testid="accounting-rule-add"
        @click="emit('add')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-plus"
            size="16"
          />
        </template>
        {{ t('accounting_settings.rule.add') }}
      </RuiButton>
      <ConfirmMenu
        :options="{ placement: 'bottom-end' }"
        close-on-content-click
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="text"
            icon
            size="sm"
            :aria-label="t('common.actions_text')"
            data-testid="accounting-rule-more-actions"
            v-bind="attrs"
          >
            <RuiIcon
              name="lu-ellipsis-vertical"
              size="18"
            />
          </RuiButton>
        </template>
        <template #default="{ ask }">
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
            data-testid="accounting-rule-reset"
            @click="ask(resetQuestion, () => emit('reset'))"
          >
            <template #prepend>
              <RuiIcon name="lu-history" />
            </template>
            {{ t('accounting_settings.rule.reset') }}
          </RuiButton>
        </template>
      </ConfirmMenu>
    </div>
  </div>
</template>
