<script setup lang="ts">
import type { ZodType } from 'zod';
import type { CalendarReminderEntry as StoredEntry } from '@/modules/calendar/reminder';
import type { CalendarEvent } from '@/modules/calendar/types';
import { startPromise } from '@shared/utils';
import CalendarReminderEntry from '@/modules/calendar/CalendarReminderEntry.vue';
import { type ReminderRow, reminderRowsSchema, splitSeconds, toSeconds } from '@/modules/calendar/reminder-forms';
import { planReminderSync, type ReminderDraft } from '@/modules/calendar/reminder-sync';
import { useCalendarReminderApi } from '@/modules/calendar/use-calendar-reminder-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useForm } from '@/modules/core/form/use-form';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';

const modelValue = defineModel<CalendarEvent>({ required: true });

const { editMode } = defineProps<{
  editMode: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const showReminders = ref<boolean>(false);
/** The reminders as the server has them. Empty for an event that does not exist yet. */
const stored = ref<StoredEntry[]>([]);
const remindInTime = ref<boolean>(false);
const latestKey = ref<number>(-1);

let nextKey = 0;

const { notify } = useNotificationDispatcher();

const {
  addCalendarReminder,
  deleteCalendarReminder,
  editCalendarReminder,
  fetchCalendarReminders,
} = useCalendarReminderApi();

/**
 * A row carries a key of its own so nothing is addressed by position, and the identifier of the
 * reminder it edits when there is one. A row the user just added has no identifier until it is
 * saved.
 */
interface EditableRow extends ReminderRow {
  key: number;
  identifier?: number;
}

const schema = computed<ZodType>(() => reminderRowsSchema({
  amountMissing: t('calendar.reminder.validation.amount.non_empty'),
  amountTooLarge: (amount, unit) => t('calendar.reminder.validation.amount.max_value', {
    amount,
    unit: t(`calendar.reminder.units.${unit}`),
  }),
  amountTooSmall: t('calendar.reminder.validation.amount.min_value'),
}));

/**
 * The rows the user edits, and the only place they live until the dialog saves.
 *
 * Nothing here reaches the server on its own: `save` reconciles the final state once the event has
 * an id. That is what lets a new event and an existing one take the same path, and what stops a row
 * being written before the user has agreed to it.
 */
const form = useForm<{ rows: EditableRow[] }, { rows: EditableRow[] }>({
  initial: (): { rows: EditableRow[] } => ({ rows: [] }),
  schema,
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: state => ({ rows: [...state.rows] }),
});

const length = computed<number>(() => form.state.rows.length);

function notifyFailure(key: 'add' | 'delete' | 'edit' | 'fetch', error: unknown): void {
  logger.error(error);
  notify({
    display: true,
    message: t(`calendar.reminder.${key}_error.message`, { message: getErrorMessage(error) }),
    title: t(`calendar.reminder.${key}_error.title`),
  });
}

async function loadStored(): Promise<void> {
  if (!editMode)
    return;

  try {
    const reminders = await fetchCalendarReminders({ identifier: get(modelValue).identifier });
    const sorted = [...reminders].sort((a, b) => a.identifier - b.identifier);
    set(stored, sorted);
    set(remindInTime, sorted.some(item => item.secsBefore === 0));

    form.reset({
      rows: sorted
        .filter(item => item.secsBefore > 0)
        .map(item => ({ ...splitSeconds(item.secsBefore), identifier: item.identifier, key: nextKey++ })),
    });
  }
  catch (error: unknown) {
    notifyFailure('fetch', error);
  }
}

// 15 minutes as default value
function addRow(secsBefore: number = 900): void {
  set(showReminders, true);
  const key = nextKey++;
  form.state.rows.push({ ...splitSeconds(secsBefore), key });
  set(latestKey, key);
}

function deleteRow(row: EditableRow): void {
  const index = form.state.rows.findIndex(item => item.key === row.key);
  if (index > -1)
    form.state.rows.splice(index, 1);
}

function toggleReminder(): void {
  if (get(length) > 0)
    set(showReminders, !get(showReminders));
}

/** Marks the row touched so a half-written one shows its message rather than staying silent. */
function commitRow(row: EditableRow): void {
  form.touch(`rows.${form.state.rows.indexOf(row)}.amount`);
}

function currentDrafts(): ReminderDraft[] {
  const drafts: ReminderDraft[] = form.state.rows.map(row => ({
    identifier: row.identifier,
    secsBefore: toSeconds(row),
  }));

  if (get(remindInTime)) {
    const existing = get(stored).find(item => item.secsBefore === 0);
    drafts.push({ identifier: existing?.identifier, secsBefore: 0 });
  }

  return drafts;
}

async function addReminders(eventId: number, secsBefore: number[]): Promise<void> {
  if (secsBefore.length === 0)
    return;

  try {
    const result = await addCalendarReminder(secsBefore.map(seconds => ({ eventId, secsBefore: seconds })));
    if (result.failed && result.failed.length > 0) {
      notify({
        display: true,
        message: t('calendar.reminder.add_error.some_failed', { ids: result.failed.join(', ') }),
        title: t('calendar.reminder.add_error.title'),
      });
    }
  }
  catch (error: unknown) {
    notifyFailure('add', error);
  }
}

/**
 * Writes the rows to the event, which the dialog calls once the event itself has been saved.
 *
 * Deletes run before adds so an interval freed in this edit can be taken again by a new row.
 */
async function save(eventId: number): Promise<void> {
  const plan = planReminderSync(get(stored), currentDrafts());

  for (const identifier of plan.deleted) {
    try {
      await deleteCalendarReminder(identifier);
    }
    catch (error: unknown) {
      notifyFailure('delete', error);
    }
  }

  for (const { identifier, secsBefore } of plan.updated) {
    try {
      await editCalendarReminder({ acknowledged: false, eventId, identifier, secsBefore });
    }
    catch (error: unknown) {
      notifyFailure('edit', error);
    }
  }

  await addReminders(eventId, plan.added);
}

onBeforeMount(() => startPromise(loadStored()));

defineExpose({
  save,
  /** The event form gates on this: vuelidate used to collect the rows on its own, zod does not. */
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div>
    <div class="border-y border-default">
      <div class="py-4 flex justify-between items-center">
        <RuiButton
          class="-ml-1"
          variant="text"
          data-testid="reminder-toggle"
          :data-expanded="showReminders"
          :class="{
            'hover:!bg-transparent active:!bg-transparent cursor-default': length === 0,
          }"
          @click="toggleReminder()"
        >
          <div class="flex gap-4">
            <div>{{ t('calendar.reminder.title') }}</div>
            <RuiBadge
              color="secondary"
              :text="length.toString()"
              placement="center"
              size="sm"
            />
            <RuiIcon
              v-if="length > 0"
              class="ml-2 transition"
              :class="{ 'transform -rotate-180': !showReminders }"
              name="lu-chevron-up"
            />
          </div>
        </RuiButton>
        <RuiButton
          color="secondary"
          size="sm"
          data-testid="reminder-add"
          @click="addRow()"
        >
          {{ t('calendar.reminder.add_reminder') }}
        </RuiButton>
      </div>
      <RuiAccordions :model-value="showReminders ? 0 : -1">
        <RuiAccordion eager>
          <template #default>
            <div
              v-if="length > 0"
              class="flex flex-col gap-2 pt-2"
            >
              <CalendarReminderEntry
                v-for="(row, index) in form.state.rows"
                :key="row.key"
                v-model:amount="row.amount"
                v-model:unit="row.unit"
                :latest="row.key === latestKey"
                :error-messages="form.errors(`rows.${index}.amount`)"
                @commit="commitRow(row)"
                @delete="deleteRow(row)"
              />
            </div>
          </template>
        </RuiAccordion>
      </RuiAccordions>

      <RuiSwitch
        v-model="remindInTime"
        color="primary"
        size="sm"
        class="ml-1 flex flex-col items-start"
      >
        <div class="text-rui-text-secondary text-sm mt-0.5">
          {{ t('calendar.reminder.notify') }}
        </div>
      </RuiSwitch>
    </div>
  </div>
</template>
