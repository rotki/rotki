<script lang="ts" setup>
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { HistoryEventQuestion } from '@/modules/history/events/types';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

const { event, canEdit = false, deleteConfirm, unlinkConfirm } = defineProps<{
  event: HistoryEventEntry;
  canEdit?: boolean;
  /** Offers delete, asking this in the menu before `delete` is emitted. */
  deleteConfirm?: HistoryEventQuestion;
  /** Offers unlink, asking this in the menu before `unlink` is emitted. */
  unlinkConfirm?: HistoryEventQuestion;
}>();

const emit = defineEmits<{
  edit: [];
  delete: [];
  unlink: [];
}>();

const vueRouter = useRouter();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
/** The action the menu is asking about in place of its list, until it is answered or closed. */
const pending = ref<'delete' | 'unlink'>();

const pendingQuestion = computed<HistoryEventQuestion | undefined>(() => {
  const action = get(pending);
  if (action === 'delete')
    return deleteConfirm;
  return action === 'unlink' ? unlinkConfirm : undefined;
});

function accept(): void {
  const action = get(pending);
  set(open, false);
  if (action === 'delete')
    emit('delete');
  else if (action === 'unlink')
    emit('unlink');
}

watch(open, (isOpen) => {
  if (!isOpen)
    set(pending, undefined);
});

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
      v-model="open"
      lazy
      :role="pendingQuestion ? 'dialog' : undefined"
      :class-names="{ menu: pendingQuestion ? 'w-72' : 'max-w-60' }"
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
      <InlineConfirm
        v-if="pendingQuestion"
        layout="panel"
        :tone="pending === 'delete' ? 'error' : 'warning'"
        :title="pendingQuestion.title"
        :message="pendingQuestion.message"
        :confirm-label="pendingQuestion.confirmLabel ?? t('common.actions.confirm')"
        @cancel="open = false"
        @confirm="accept()"
      />
      <template v-else>
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
          v-if="unlinkConfirm"
          variant="list"
          data-testid="row-unlink"
          @click.stop="pending = 'unlink'"
        >
          <template #prepend>
            <RuiIcon
              class="text-rui-text-secondary"
              name="lu-unlink"
            />
          </template>
          {{ t('transactions.events.actions.unlink') }}
        </RuiButton>
        <template v-if="deleteConfirm">
          <RuiDivider class="my-1" />
          <RuiButton
            variant="list"
            color="error"
            data-testid="row-delete"
            @click.stop="pending = 'delete'"
          >
            <template #prepend>
              <RuiIcon name="lu-trash-2" />
            </template>
            {{ t('transactions.events.actions.delete') }}
          </RuiButton>
        </template>
      </template>
    </RuiMenu>
  </div>
</template>
