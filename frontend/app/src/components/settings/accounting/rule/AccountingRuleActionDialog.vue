<script setup lang="ts">
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import AccountingRuleEventsDialog from '@/components/settings/accounting/rule/AccountingRuleEventsDialog.vue';

interface Props {
  hasEventSpecificRule: boolean;
  hasGeneralRule: boolean;
  eventId: number;
  generalRule?: AccountingRuleEntry;
  eventSpecificRule?: AccountingRuleEntry;
  eventIds?: number[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'select', action: 'add-general' | 'add-event-specific' | 'edit-general' | 'edit-event-specific'): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const display = ref<boolean>(true);

function onSelect(action: 'add-general' | 'add-event-specific' | 'edit-general' | 'edit-event-specific') {
  emit('select', action);
  set(display, false);
}

watch(display, (value) => {
  if (!value)
    emit('close');
});

const affectedEventsCount = computed<number>(() => props.eventIds?.length ?? 0);

const showEventsList = ref<boolean>(false);
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

          <RuiCard
            variant="outlined"
            class="!rounded-md"
          >
            <div class="space-y-3">
              <div
                class="flex gap-2"
              >
                <RuiButton
                  variant="outlined"
                  color="primary"
                  class="w-full justify-start"
                  @click="onSelect('edit-event-specific')"
                >
                  <template #prepend>
                    <RuiIcon
                      size="20"
                      name="lu-pencil"
                    />
                  </template>
                  <div class="text-left ml-1">
                    <div>{{ t('accounting_settings.rule.action_dialog.edit_event_specific') }}</div>
                    <div class="text-xs text-rui-text-secondary mb-1">
                      {{ t('accounting_settings.rule.action_dialog.affects_events', { count: affectedEventsCount }) }}
                    </div>
                  </div>
                </RuiButton>
                <RuiButton
                  variant="text"
                  size="sm"
                  color="primary"
                  class="!px-4"
                  @click="showEventsList = true"
                >
                  {{ t('accounting_settings.rule.action_dialog.view_affected_events') }}
                  <template #append>
                    <RuiIcon
                      name="lu-arrow-right"
                      size="20"
                    />
                  </template>
                </RuiButton>
              </div>

              <RuiButton
                v-if="affectedEventsCount > 1"
                variant="outlined"
                color="primary"
                class="w-full justify-start"
                @click="onSelect('add-event-specific')"
              >
                <template #prepend>
                  <RuiIcon
                    size="20"
                    name="lu-plus"
                  />
                </template>
                <div class="text-left ml-1">
                  <div>{{ t('accounting_settings.rule.action_dialog.add_new_event_specific') }}</div>
                  <div class="text-xs text-rui-text-secondary mb-1">
                    {{ t('accounting_settings.rule.action_dialog.only_this_event') }}
                  </div>
                </div>
              </RuiButton>
            </div>
          </RuiCard>
        </div>

        <div
          v-else-if="hasGeneralRule"
          class="space-y-3"
        >
          <div class="text-rui-text-secondary text-sm">
            {{ t('accounting_settings.rule.action_dialog.general_rule_exists') }}
          </div>

          <RuiCard
            variant="outlined"
            class="!rounded-md"
          >
            <div class="space-y-3">
              <RuiButton
                variant="outlined"
                color="primary"
                class="w-full justify-start"
                @click="onSelect('edit-general')"
              >
                <template #prepend>
                  <RuiIcon
                    size="20"
                    name="lu-pencil"
                  />
                </template>
                <div class="text-left ml-1">
                  <div>{{ t('accounting_settings.rule.action_dialog.edit_general') }}</div>
                  <div class="text-xs text-rui-text-secondary mb-1">
                    {{ t('accounting_settings.rule.action_dialog.affects_all_similar') }}
                  </div>
                </div>
              </RuiButton>

              <RuiButton
                variant="outlined"
                color="primary"
                class="w-full justify-start"
                @click="onSelect('add-event-specific')"
              >
                <template #prepend>
                  <RuiIcon
                    size="20"
                    name="lu-plus"
                  />
                </template>
                <div class="text-left ml-1">
                  <div>{{ t('accounting_settings.rule.action_dialog.add_event_specific') }}</div>
                  <div class="text-xs text-rui-text-secondary mb-1">
                    {{ t('accounting_settings.rule.action_dialog.override_general') }}
                  </div>
                </div>
              </RuiButton>
            </div>
          </RuiCard>
        </div>

        <div
          v-else
          class="space-y-3"
        >
          <div class="text-rui-text-secondary text-sm">
            {{ t('accounting_settings.rule.action_dialog.no_rule_exists') }}
          </div>

          <RuiCard
            variant="outlined"
            class="!rounded-md"
          >
            <div class="space-y-3">
              <RuiButton
                variant="outlined"
                color="primary"
                class="w-full justify-start"
                @click="onSelect('add-general')"
              >
                <template #prepend>
                  <RuiIcon
                    size="20"
                    name="lu-plus"
                  />
                </template>
                <div class="text-left ml-1">
                  <div>{{ t('accounting_settings.rule.action_dialog.add_general') }}</div>
                  <div class="text-xs text-rui-text-secondary mb-1">
                    {{ t('accounting_settings.rule.action_dialog.for_all_similar') }}
                  </div>
                </div>
              </RuiButton>

              <RuiButton
                variant="outlined"
                color="primary"
                class="w-full justify-start"
                @click="onSelect('add-event-specific')"
              >
                <template #prepend>
                  <RuiIcon
                    size="20"
                    name="lu-plus"
                  />
                </template>
                <div class="text-left ml-1">
                  <div>{{ t('accounting_settings.rule.action_dialog.add_event_specific') }}</div>
                  <div class="text-xs text-rui-text-secondary mb-1">
                    {{ t('accounting_settings.rule.action_dialog.only_this_event') }}
                  </div>
                </div>
              </RuiButton>
            </div>
          </RuiCard>
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
