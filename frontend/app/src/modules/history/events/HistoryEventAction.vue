<script lang="ts" setup>
import type { HistoryEventEntry } from '@/modules/history/events/schemas';

const { event, canUnlink, canEdit = false, canDelete = false } = defineProps<{
  event: HistoryEventEntry;
  canUnlink?: boolean;
  canEdit?: boolean;
  canDelete?: boolean;
}>();

const emit = defineEmits<{
  edit: [];
  delete: [];
  unlink: [];
}>();

const vueRouter = useRouter();

const { t } = useI18n({ useScope: 'global' });

function onEditRule(): void {
  const entry = event;

  const data = {
    counterparty: '',
    eventId: entry.identifier.toString(),
    eventSubtype: entry.eventSubtype,
    eventType: entry.eventType,
  };

  if ('counterparty' in entry)
    data.counterparty = entry.counterparty ?? '';

  vueRouter.push({
    path: '/settings/accounting',
    query: { 'edit-rule': 'true', ...data },
  });
}
</script>

<template>
  <div class="flex items-center">
    <RuiMenu
      lazy
      :class-names="{ menu: 'max-w-60' }"
      :options="{ autoUpdate: { resize: false, scroll: false }, placement: 'bottom-end' }"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <RuiButton
          icon
          variant="text"
          class="p-2.5!"
          :aria-label="t('common.actions.more')"
          data-testid="row-actions-menu"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-ellipsis-vertical"
            size="20"
          />
        </RuiButton>
      </template>
      <RuiButton
        v-if="canEdit"
        variant="list"
        data-testid="row-edit"
        @click="emit('edit')"
      >
        <template #prepend>
          <RuiIcon
            class="text-rui-text-secondary"
            name="lu-pencil"
          />
        </template>
        {{ t('transactions.events.actions.edit') }}
      </RuiButton>
      <RuiButton
        variant="list"
        @click="onEditRule()"
      >
        <template #prepend>
          <RuiIcon
            class="text-rui-text-secondary"
            name="lu-file-spreadsheet"
          />
        </template>
        {{ t('accounting_settings.rule.edit') }}
      </RuiButton>
      <RuiButton
        v-if="canUnlink"
        variant="list"
        data-testid="row-unlink"
        @click="emit('unlink')"
      >
        <template #prepend>
          <RuiIcon
            class="text-rui-text-secondary"
            name="lu-unlink"
          />
        </template>
        {{ t('transactions.events.actions.unlink') }}
      </RuiButton>
      <template v-if="canDelete">
        <RuiDivider class="my-1" />
        <RuiButton
          variant="list"
          color="error"
          data-testid="row-delete"
          @click="emit('delete')"
        >
          <template #prepend>
            <RuiIcon name="lu-trash-2" />
          </template>
          {{ t('transactions.events.actions.delete') }}
        </RuiButton>
      </template>
    </RuiMenu>
  </div>
</template>
