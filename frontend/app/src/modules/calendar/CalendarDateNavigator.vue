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

// Both the Today label and the chevron reflect the same "already on today"
// state so the pair reads as a single control — the chevron used to stay
// primary-outlined while Today greyed out, breaking the visual group.
const alreadyOnToday = computed<boolean>(() => visibleDate.isSame(today, 'day'));

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
  <!--
    Today + chevron are rendered as adjacent siblings in a plain flex wrapper
    rather than inside a RuiButtonGroup. Nesting a RuiMenu as a group child
    was causing the menu to flicker open/close on Today clicks — the group
    intercepts each child's `update:model-value` as a button-selection event
    and injects `active`/`color`/`size` props into the menu's VNode, which
    destabilised its open state. Here the two buttons share a visual seam
    via `!rounded-r-none` / `!rounded-l-none` + `-ml-px`.

    The menu stays `persistent` so that interacting with the nested
    DateTimePicker (which teleports its own time/date overlays outside this
    component's DOM subtree) doesn't count as an outside click and dismiss
    the Go-to-date popup. Close paths: pick a date and hit the corner-down
    submit button, press Enter/Escape inside the popup, or click the
    chevron again to toggle.
  -->
  <div class="flex">
    <RuiButton
      color="primary"
      variant="outlined"
      size="xl"
      class="!rounded-r-none"
      :disabled="alreadyOnToday"
      @click="emit('set-today')"
    >
      {{ t('calendar.today') }}
    </RuiButton>
    <RuiMenu
      v-model="open"
      persistent
    >
      <template #activator="{ attrs }">
        <RuiButton
          color="primary"
          variant="outlined"
          icon
          size="xl"
          class="!rounded-l-none -ml-px !rounded"
          v-bind="attrs"
        >
          <RuiIcon name="lu-chevron-down" />
        </RuiButton>
      </template>
      <div
        class="p-4 flex items-start"
        tabindex="-1"
        @keydown.esc="open = false"
      >
        <DateTimePicker
          v-model="datetime"
          variant="outlined"
          class="w-[16rem] [&_fieldset]:!rounded-r-none"
          type="epoch"
          dense
          :label="t('calendar.go_to_date')"
          @keydown.enter="goToSelectedDate()"
        />
        <RuiButton
          color="primary"
          class="!rounded-l-none !p-2 !py-2.5"
          @click="goToSelectedDate()"
        >
          <RuiIcon
            name="lu-corner-down-left"
            size="20"
          />
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>
