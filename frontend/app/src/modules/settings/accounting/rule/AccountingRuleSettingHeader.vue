<script setup lang="ts">
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

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

const open = ref<boolean>(false);
/** The menu asks about the reset in place of its items, until it is answered or closed. */
const confirmingReset = ref<boolean>(false);

function acceptReset(): void {
  set(open, false);
  emit('reset');
}

watch(open, (isOpen) => {
  if (!isOpen)
    set(confirmingReset, false);
});
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
      <RuiMenu
        v-model="open"
        :role="confirmingReset ? 'dialog' : undefined"
        :class-names="{ menu: confirmingReset ? 'w-72' : '' }"
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
        <InlineConfirm
          v-if="confirmingReset"
          layout="panel"
          tone="error"
          :message="t('accounting_settings.rule.confirm_reset')"
          :confirm-label="t('accounting_settings.rule.reset')"
          @cancel="open = false"
          @confirm="acceptReset()"
        />
        <template v-else>
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
            @click.stop="confirmingReset = true"
          >
            <template #prepend>
              <RuiIcon name="lu-history" />
            </template>
            {{ t('accounting_settings.rule.reset') }}
          </RuiButton>
        </template>
      </RuiMenu>
    </div>
  </div>
</template>
