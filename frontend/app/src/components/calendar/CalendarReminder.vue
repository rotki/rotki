<script setup lang="ts">
import type { CalendarEvent } from '@/types/history/calendar';
import type { CalendarReminderTemporaryPayload, CalenderReminderPayload } from '@/types/history/calendar/reminder';
import CalendarReminderEntry from '@/components/calendar/CalendarReminderEntry.vue';
import { useCalendarReminderApi } from '@/composables/history/calendar/reminder';
import { useNotificationsStore } from '@/store/notifications';
import { logger } from '@/utils/logging';

const modelValue = defineModel<CalendarEvent>({ required: true });

const props = defineProps<{
  editMode: boolean;
}>();

const { t } = useI18n();

const showReminders = ref<boolean>(false);
const temporaryData = ref<CalendarReminderTemporaryPayload[]>([]);
const newIdCreated = ref<number>(-1);

const { notify } = useNotificationsStore();

const {
  addCalendarReminder,
  deleteCalendarReminder,
  editCalendarReminder,
  fetchCalendarReminders,
} = useCalendarReminderApi();

const length = computed<number>(() => get(temporaryData).filter(item => item.secsBefore > 0).length);

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
  catch (error: any) {
    logger.error(error);
    notify({
      display: true,
      message: t('calendar.reminder.add_error.message', {
        message: error.message,
      }),
      title: t('calendar.reminder.add_error.title'),
    });
  }
}

async function refreshTemporaryData() {
  if (!props.editMode) {
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
  catch (error: any) {
    logger.error(error);
    notify({
      display: true,
      message: t('calendar.reminder.fetch_error.message', {
        message: error.message,
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

  if (!props.editMode || isSameSecsBeforeExist(secsBefore) || inTimeReminder) {
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

  if (!data.isTemporary && props.editMode) {
    try {
      await deleteCalendarReminder(data.identifier);
    }
    catch (error: any) {
      logger.error(error);
      notify({
        display: true,
        message: t('calendar.reminder.delete_error.message', {
          message: error.message,
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

  if (props.editMode) {
    if (!data.isTemporary) {
      try {
        await editCalendarReminder({
          eventId: item.identifier,
          identifier: data.identifier,
          secsBefore,
        });
      }
      catch (error: any) {
        logger.error(error);
        notify({
          display: true,
          message: t('calendar.reminder.edit_error.message', {
            message: error.message,
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
});
</script>

<template>
  <div>
    <div class="border-y border-default">
      <div class="py-4 flex justify-between items-center">
        <RuiButton
          class="-ml-1"
          variant="text"
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
              <template v-for="(data, index) in temporaryData">
                <CalendarReminderEntry
                  v-if="data.secsBefore > 0"
                  :key="data.identifier"
                  :model-value="data"
                  :latest="data.identifier === newIdCreated"
                  @delete="deleteData(index)"
                  @update:model-value="updateData(index, $event)"
                />
              </template>
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
