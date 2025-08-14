<script setup lang="ts">
import type { RuiButton } from '@rotki/ui-library';
import dayjs, { type Dayjs } from 'dayjs';
import { useTemplateRef } from 'vue';

const model = defineModel<Dayjs>({ required: true });

defineProps<{
  visibleDate: Dayjs;
  today: Dayjs;
}>();

const emit = defineEmits<{
  (e: 'set-today'): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const datetime = ref<number>(0);
const open = ref(false);

const activatorRef = ref();
const menuContainerRef = useTemplateRef<InstanceType<typeof HTMLDivElement>>('menuContainerRef');

const { focused: menuFocusedWithin } = useFocusWithin(menuContainerRef);
const { focused: activatorFocusedWithin } = useFocusWithin(activatorRef);

const anyFocused = computed(() => get(activatorFocusedWithin) || get(menuFocusedWithin));
const debouncedAnyFocused = debouncedRef(anyFocused, 100);
const usedAnyFocused = logicOr(anyFocused, debouncedAnyFocused);

function goToSelectedDate() {
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

watch(usedAnyFocused, (curr, prev) => {
  if (prev && !curr) {
    set(open, false);
  }
});
</script>

<template>
  <RuiButtonGroup
    color="primary"
    variant="outlined"
  >
    <RuiButton
      :disabled="visibleDate.isSame(today, 'day')"
      @click="emit('set-today')"
    >
      {{ t('calendar.today') }}
    </RuiButton>
    <RuiMenu
      v-model="open"
      persistent
      wrapper-class="h-full"
    >
      <template #activator="{ attrs }">
        <RuiButton
          ref="activatorRef"
          size="sm"
          class="!p-2 !outline-none h-full"
          color="primary"
          variant="outlined"
          v-bind="attrs"
        >
          <RuiIcon
            size="20"
            name="lu-chevron-down"
          />
        </RuiButton>
      </template>
      <div
        ref="menuContainerRef"
        class="p-4 flex items-start"
        tabindex="-1"
      >
        <RuiDateTimePicker
          v-model="datetime"
          color="primary"
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
  </RuiButtonGroup>
</template>
