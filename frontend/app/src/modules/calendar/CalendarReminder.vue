<script setup lang="ts">
import type { ZodType } from 'zod';
import type { CalendarReminderTemporaryPayload, CalenderReminderPayload } from '@/modules/calendar/reminder';
import type { CalendarEvent } from '@/modules/calendar/types';
import { startPromise } from '@shared/utils';
import CalendarReminderEntry from '@/modules/calendar/CalendarReminderEntry.vue';
import { type ReminderRow, reminderRowsSchema, splitSeconds, toSeconds } from '@/modules/calendar/reminder-forms';
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
const temporaryData = ref<CalendarReminderTemporaryPayload[]>([]);
const newIdCreated = ref<number>(-1);

const { notify } = useNotificationDispatcher();

const {
  addCalendarReminder,
  deleteCalendarReminder,
  editCalendarReminder,
  fetchCalendarReminders,
} = useCalendarReminderApi();

const length = computed<number>(() => get(temporaryData).filter(item => item.secsBefore > 0).length);

/** A row carries the identifier of the reminder it edits, so nothing is addressed by position. */
interface EditableRow extends ReminderRow {
  identifier: number;
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
 * The rows the user edits. Persistence still happens per reminder against its own endpoints; this
 * form exists so a half-written row is ordinary state that the event form can gate on, rather than
 * something the row hides until it happens to be valid.
 */
const form = useForm<{ rows: EditableRow[] }, { rows: EditableRow[] }>({
  initial: (): { rows: EditableRow[] } => ({ rows: [] }),
  schema,
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: state => ({ rows: [...state.rows] }),
});

/** Rebuilt only when the stored reminders change, so an in-progress edit is not overwritten. */
watchImmediate(temporaryData, (data) => {
  const next = data
    .filter(item => item.secsBefore > 0)
    .map(item => ({ ...splitSeconds(item.secsBefore), identifier: item.identifier }));

  const current = form.state.rows;
  const unchanged = next.length === current.length
    && next.every((row, index) => row.identifier === current[index].identifier
      && toSeconds(row) === toSeconds(current[index]));

  if (!unchanged)
    form.reset({ rows: next });
}, { deep: true });

function indexOfIdentifier(identifier: number): number {
  return get(temporaryData).findIndex(item => item.identifier === identifier);
}

/**
 * Persists a row once the user leaves it. An invalid row is not sent, exactly as before, but it is
 * no longer invisible: it stays in the form state, shows its message, and blocks the event's save.
 */
function commitRow(row: EditableRow): void {
  form.touch(`rows.${form.state.rows.indexOf(row)}.amount`);

  if (!get(form.valid))
    return;

  const index = indexOfIdentifier(row.identifier);
  if (index === -1)
    return;

  const stored = get(temporaryData)[index];
  const secsBefore = toSeconds(row);
  if (stored.secsBefore !== secsBefore)
    startPromise(updateData(index, { ...stored, secsBefore }));
}

function deleteRow(row: EditableRow): void {
  const index = indexOfIdentifier(row.identifier);
  if (index > -1)
    startPromise(deleteData(index));
}

const remindInTime = computed<boolean>({
  get() {
    return get(temporaryData).some(item => item.secsBefore === 0);
  },
  async set(value: boolean) {
    if (!value) {
      const index = get(temporaryData).findIndex(item => item.secsBefore === 0);
      if (index > -1)
        await deleteData(index);
    }
    else {
      await addReminder(0, true);
    }
  },
});

async function addCalendarReminderHandler(reminders: CalenderReminderPayload[]) {
  try {
    const result = await addCalendarReminder(reminders);
    if (result.failed && result.failed.length > 0) {
      notify({
        display: true,
        message: t('calendar.reminder.add_error.some_failed', {
          ids: result.failed.join(', '),
        }),
        title: t('calendar.reminder.add_error.title'),
      });
    }
  }
  catch (error: unknown) {
    logger.error(error);
    notify({
      display: true,
      message: t('calendar.reminder.add_error.message', {
        message: getErrorMessage(error),
      }),
      title: t('calendar.reminder.add_error.title'),
    });
  }
}

async function refreshTemporaryData() {
  if (!editMode) {
    return;
  }
  const item = get(modelValue);
  try {
    const identifier = item.identifier;
    const reminders = await fetchCalendarReminders({ identifier });
    const sortedReminders = reminders.sort((a, b) => a.identifier - b.identifier);
    const oldData = [...get(temporaryData)].filter(item => item.isTemporary);
    const newData = [...sortedReminders.map(item => ({ ...item, isTemporary: false })), ...oldData];
    set(temporaryData, newData);
  }
  catch (error: unknown) {
    logger.error(error);
    notify({
      display: true,
      message: t('calendar.reminder.fetch_error.message', {
        message: getErrorMessage(error),
      }),
      title: t('calendar.reminder.fetch_error.title'),
    });
  }
}

function isSameSecsBeforeExist(seconds: number) {
  return get(temporaryData)
    .filter(item => !item.isTemporary)
    .some(item => item.secsBefore === seconds);
}

// 15 minutes as default value
async function addReminder(secsBefore: number = 900, inTimeReminder = false) {
  if (!inTimeReminder)
    set(showReminders, true);

  const item = get(modelValue);

  if (!editMode || isSameSecsBeforeExist(secsBefore) || inTimeReminder) {
    const newId = Date.now();
    const newData: CalendarReminderTemporaryPayload = {
      identifier: newId,
      isTemporary: true,
      secsBefore,
    };

    set(temporaryData, [...get(temporaryData), newData]);

    set(newIdCreated, newId);
  }
  else {
    await addCalendarReminderHandler([
      {
        eventId: item.identifier,
        secsBefore,
      },
    ]);
    await refreshTemporaryData();
  }
}

function toggleReminder() {
  if (get(temporaryData).length > 0)
    set(showReminders, !get(showReminders));
}

async function deleteData(index: number) {
  const temp = [...get(temporaryData)];
  const data = temp[index];

  if (!data.isTemporary && editMode) {
    try {
      await deleteCalendarReminder(data.identifier);
    }
    catch (error: unknown) {
      logger.error(error);
      notify({
        display: true,
        message: t('calendar.reminder.delete_error.message', {
          message: getErrorMessage(error),
        }),
        title: t('calendar.reminder.delete_error.title'),
      });
    }
    await refreshTemporaryData();
  }
  else {
    temp.splice(index, 1);
    set(temporaryData, temp);
  }
}

async function updateData(index: number, { secsBefore }: CalendarReminderTemporaryPayload) {
  const item = get(modelValue);
  const temp = [...get(temporaryData)];
  const data = temp[index];

  if (editMode) {
    if (!data.isTemporary) {
      try {
        await editCalendarReminder({
          acknowledged: false,
          eventId: item.identifier,
          identifier: data.identifier,
          secsBefore,
        });
      }
      catch (error: unknown) {
        logger.error(error);
        notify({
          display: true,
          message: t('calendar.reminder.edit_error.message', {
            message: getErrorMessage(error),
          }),
          title: t('calendar.reminder.edit_error.title'),
        });
      }

      await refreshTemporaryData();
    }
    else if (!isSameSecsBeforeExist(secsBefore)) {
      await addCalendarReminderHandler([
        {
          eventId: item.identifier,
          secsBefore,
        },
      ]);
      await deleteData(index);
      await refreshTemporaryData();
    }
  }
  else {
    temp[index].secsBefore = secsBefore;
    set(temporaryData, temp);
  }
}

async function saveTemporaryReminder(eventId: number) {
  const temporary = get(temporaryData).filter(item => item.isTemporary);

  if (temporary.length > 0) {
    const savedSeconds = get(temporaryData)
      .filter(item => !item.isTemporary)
      .map(item => item.secsBefore);

    const secsBeforeToSave: number[] = [];
    temporary.forEach(({ secsBefore }) => {
      if (!savedSeconds.includes(secsBefore) && !secsBeforeToSave.includes(secsBefore))
        secsBeforeToSave.push(secsBefore);
    });

    await addCalendarReminderHandler(secsBeforeToSave.map(secsBefore => ({ eventId, secsBefore })));
  }
}

onBeforeMount(() => refreshTemporaryData());

defineExpose({
  saveTemporaryReminder,
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
          @click="addReminder()"
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
                :key="row.identifier"
                v-model:amount="row.amount"
                v-model:unit="row.unit"
                :latest="row.identifier === newIdCreated"
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
