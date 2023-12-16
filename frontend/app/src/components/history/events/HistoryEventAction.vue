<script lang="ts" setup>
import { Routes } from '@/router/routes';
import type { HistoryEventEntry } from '@/types/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
}>();

const vueRouter = useRouter();

const { event } = toRefs(props);

const { t } = useI18n();

function onEditRule() {
  const entry = get(event);

  const data = {
    eventSubtype: entry.eventSubtype,
    eventType: entry.eventType,
    counterparty: '',
  };

  if ('counterparty' in entry)
    data.counterparty = entry.counterparty ?? '';

  vueRouter.push({
    path: Routes.SETTINGS_ACCOUNTING,
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
            name="more-2-fill"
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
              name="pencil-line"
            />
          </template>
          {{ t('accounting_settings.rule.edit') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>
