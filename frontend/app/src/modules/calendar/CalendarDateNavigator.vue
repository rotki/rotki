<script setup lang="ts">
import dayjs, { type Dayjs } from 'dayjs';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

const model = defineModel<Dayjs>({ required: true });

const { visibleDate, today } = defineProps<{
  visibleDate: Dayjs;
  today: Dayjs;
}>();

const emit = defineEmits<{
  'set-today': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const datetime = ref<number>(0);
const open = ref<boolean>(false);

const alreadyOnToday = computed<boolean>(() => visibleDate.isSame(today, 'month') && get(model).isSame(today, 'day'));

function goToSelectedDate(): void {
  set(model, dayjs(get(datetime) * 1000));
  set(open, false);
}

watch(
  model,
  (model) => {
    set(datetime, get(model).unix());
  },
  {
    immediate: true,
  },
);
</script>

<template>
  <div class="flex items-center">
    <RuiButton
      color="primary"
      variant="outlined"
      size="sm"
      class="h-8! rounded-r-none!"
      :disabled="alreadyOnToday"
      data-testid="calendar-today"
      @click="emit('set-today')"
    >
      {{ t('calendar.today') }}
    </RuiButton>
    <RuiMenu
      v-model="open"
      class="flex"
      :options="{ placement: 'bottom-start' }"
      persistent
    >
      <template #activator="{ attrs }">
        <RuiButton
          color="primary"
          variant="outlined"
          icon
          size="sm"
          class="size-8! rounded-l-none! rounded-r-rui-control! -ml-px"
          :aria-label="t('calendar.go_to_date')"
          v-bind="attrs"
        >
          <RuiIcon name="lu-chevron-down" />
        </RuiButton>
      </template>
      <div
        class="p-4 flex items-end"
        tabindex="-1"
        @keydown.esc="open = false"
      >
        <DateTimePicker
          v-model="datetime"
          class="w-64 [&_fieldset]:rounded-r-none!"
          type="epoch"
          dense
          details="hidden"
          :label="t('calendar.go_to_date')"
          @keydown.enter="goToSelectedDate()"
        />
        <RuiButton
          color="primary"
          icon
          class="size-8! rounded-l-none! rounded-r-rui-control!"
          :aria-label="t('calendar.go_to_date')"
          @click="goToSelectedDate()"
        >
          <RuiIcon
            name="lu-corner-down-left"
            size="16"
          />
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>
