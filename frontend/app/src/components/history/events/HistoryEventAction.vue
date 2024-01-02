<script lang="ts" setup>
import { type HistoryEventEntry } from '@/types/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
}>();

const vueRouter = useRouter();

const { event } = toRefs(props);

const { t } = useI18n();

const onEditRule = () => {
  const entry = get(event);

  const data = {
    eventSubtype: entry.eventSubtype,
    eventType: entry.eventType,
    counterparty: ''
  };

  if ('counterparty' in entry) {
    data.counterparty = entry.counterparty ?? '';
  }

  vueRouter.push({
    path: '/settings/accounting',
    query: { 'edit-rule': 'true', ...data }
  });
};
</script>

<template>
  <div class="flex items-center">
    <VMenu
      max-width="250px"
      min-width="200px"
      left
      offset-y
      transition="slide-y-transition"
    >
      <template #activator="{ on }">
        <RuiButton class="!p-2" icon variant="text" v-on="on">
          <RuiIcon name="more-2-fill" size="20" />
        </RuiButton>
      </template>
      <div class="py-2">
        <RuiButton variant="list" @click="onEditRule()">
          <template #prepend>
            <RuiIcon class="text-rui-text-secondary" name="pencil-line" />
          </template>
          {{ t('accounting_settings.rule.edit') }}
        </RuiButton>
      </div>
    </VMenu>
  </div>
</template>
