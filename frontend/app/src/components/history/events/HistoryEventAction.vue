<script lang="ts" setup>
import type { HistoryEventEntry } from '@/types/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
}>();

const vueRouter = useRouter();

const { event } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

function onEditRule() {
  const entry = get(event);

  const data = {
    counterparty: '',
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
      menu-class="max-w-[15rem]"
      :popper="{ placement: 'bottom-end' }"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <RuiButton
          icon
          variant="text"
          class="!p-2.5"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-ellipsis-vertical"
            size="20"
          />
        </RuiButton>
      </template>
      <div class="py-2">
        <RuiButton
          variant="list"
          @click="onEditRule()"
        >
          <template #prepend>
            <RuiIcon
              class="text-rui-text-secondary"
              name="lu-pencil"
            />
          </template>
          {{ t('accounting_settings.rule.edit') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>
