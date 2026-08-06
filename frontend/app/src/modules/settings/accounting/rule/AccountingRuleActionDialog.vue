<script setup lang="ts">
import type { AccountingRuleAction } from '@/modules/settings/types/accounting';
import AccountingRuleActionButton from '@/modules/settings/accounting/rule/AccountingRuleActionButton.vue';
import AccountingRuleEventsDialog from '@/modules/settings/accounting/rule/AccountingRuleEventsDialog.vue';
import AccountingRuleViewEventsButton from '@/modules/settings/accounting/rule/AccountingRuleViewEventsButton.vue';

interface Props {
  hasEventSpecificRule: boolean;
  hasGeneralRule: boolean;
  eventIds?: number[];
}

const { eventIds } = defineProps<Props>();

const emit = defineEmits<{
  close: [];
  select: [action: AccountingRuleAction];
}>();

const { t } = useI18n({ useScope: 'global' });

const display = ref<boolean>(true);
const showEventsList = ref<boolean>(false);

const affectedEventsCount = computed<number>(() => eventIds?.length ?? 0);

function onSelect(action: AccountingRuleAction) {
  emit('select', action);
  set(display, false);
}

watch(display, (value) => {
  if (!value)
    emit('close');
});
</script>

<template>
  <RuiDialog
    v-model="display"
    max-width="600"
  >
    <RuiCard content-class="!pt-0">
      <template #header>
        {{ t('accounting_settings.rule.action_dialog.title') }}
      </template>

      <div class="space-y-4">
        <div
          v-if="hasEventSpecificRule"
          class="space-y-3"
        >
          <div class="text-rui-text-secondary text-sm">
            {{ t('accounting_settings.rule.action_dialog.event_specific_exists') }}
          </div>

          <div class="space-y-2">
            <div class="flex gap-2 relative">
              <AccountingRuleActionButton
                icon="lu-pencil"
                :title="t('accounting_settings.rule.action_dialog.edit_event_specific')"
                :subtitle="t('accounting_settings.rule.action_dialog.affects_events', { count: affectedEventsCount })"
                @click="onSelect('edit-event-specific')"
              />
              <AccountingRuleViewEventsButton
                @click="showEventsList = true"
              />
            </div>

            <AccountingRuleActionButton
              v-if="affectedEventsCount > 1"
              icon="lu-plus"
              :title="t('accounting_settings.rule.action_dialog.add_new_event_specific')"
              :subtitle="t('accounting_settings.rule.action_dialog.only_this_event')"
              @click="onSelect('add-event-specific')"
            />
          </div>
        </div>

        <div
          v-else-if="hasGeneralRule"
          class="space-y-3"
        >
          <div class="text-rui-text-secondary text-sm">
            {{ t('accounting_settings.rule.action_dialog.general_rule_exists') }}
          </div>

          <div class="space-y-2">
            <AccountingRuleActionButton
              icon="lu-pencil"
              :title="t('accounting_settings.rule.action_dialog.edit_general')"
              :subtitle="t('accounting_settings.rule.action_dialog.affects_all_similar')"
              @click="onSelect('edit-general')"
            />

            <AccountingRuleActionButton
              icon="lu-plus"
              :title="t('accounting_settings.rule.action_dialog.add_event_specific')"
              :subtitle="t('accounting_settings.rule.action_dialog.override_general')"
              @click="onSelect('add-event-specific')"
            />
          </div>
        </div>

        <div
          v-else
          class="space-y-3"
        >
          <div class="text-rui-text-secondary text-sm">
            {{ t('accounting_settings.rule.action_dialog.no_rule_exists') }}
          </div>

          <div class="space-y-2">
            <AccountingRuleActionButton
              icon="lu-plus"
              :title="t('accounting_settings.rule.action_dialog.add_general')"
              :subtitle="t('accounting_settings.rule.action_dialog.for_all_similar')"
              @click="onSelect('add-general')"
            />

            <AccountingRuleActionButton
              icon="lu-plus"
              :title="t('accounting_settings.rule.action_dialog.add_event_specific')"
              :subtitle="t('accounting_settings.rule.action_dialog.only_this_event')"
              @click="onSelect('add-event-specific')"
            />
          </div>
        </div>
      </div>

      <template #footer>
        <div class="grow" />
        <RuiButton
          color="primary"
          variant="text"
          @click="display = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
      </template>
    </RuiCard>

    <AccountingRuleEventsDialog
      v-if="showEventsList && eventIds"
      :event-ids="eventIds"
      @close="showEventsList = false"
    />
  </RuiDialog>
</template>
