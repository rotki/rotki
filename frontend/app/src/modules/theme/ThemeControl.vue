<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useInterop } from '@/composables/electron-interop';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { Theme } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    darkModeEnabled: boolean;
    menu?: boolean;
  }>(),
  {
    menu: false,
  },
);

const { darkModeEnabled } = toRefs(props);

const automaticSymbol = 'A';

const { t } = useI18n();
const { isPackaged, setSelectedTheme } = useInterop();

const frontendSettingsStore = useFrontendSettingsStore();
const { updateSetting } = frontendSettingsStore;
const { selectedTheme } = storeToRefs(frontendSettingsStore);

const isAutomatic = computed<boolean>(() => get(selectedTheme) === Theme.AUTO);

const labels = computed(() => [
  t('theme_switch.dark'),
  t('theme_switch.auto'),
  t('theme_switch.light'),
]);

const tooltip = computed(() => {
  const mode = get(darkModeEnabled)
    ? t('theme_switch.light')
    : t('theme_switch.dark');
  return t('theme_switch.tooltip', { mode });
});

async function toggleSelectedTheme() {
  const newTheme = get(darkModeEnabled) ? Theme.LIGHT : Theme.DARK;
  await changeSelectedTheme(newTheme);
}

async function changeSelectedTheme(selectedTheme: Theme) {
  await updateSetting({ selectedTheme });
  if (isPackaged) {
    await setSelectedTheme(selectedTheme);
  }
}
</script>

<template>
  <div class="relative">
    <RuiMenu
      v-if="!menu"
      menu-class="w-[16rem]"
      :popper="{ placement: 'bottom-end' }"
    >
      <template #activator="{ attrs }">
        <MenuTooltipButton
          :tooltip="tooltip"
          class-name="theme-switch"
          @click="toggleSelectedTheme()"
        >
          <RuiIcon
            v-if="darkModeEnabled"
            name="lu-moon"
          />
          <RuiIcon
            v-else
            name="lu-sun"
          />
          <div
            v-if="isAutomatic"
            class="absolute -top-1 right-0"
          >
            {{ automaticSymbol }}
          </div>
        </MenuTooltipButton>
        <RuiButton
          class="p-0 absolute z-10 right-0  top-[1.775rem] w-4 h-4 lg:top-8 lg:w-[1.125rem] lg:h-[1.125rem] !bg-rui-grey-100 text-black dark:text-white dark:!bg-black"
          icon
          variant="text"
          size="sm"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-chevron-down"
            size="16"
          />
        </RuiButton>
      </template>
      <div>
        <label
          class="px-2 py-5 flex"
          for="theme-switch-slider"
        >
          <RuiSlider
            id="theme-switch-slider"
            :model-value="selectedTheme"
            class="h-32 w-8"
            data-cy="theme-switch__input"
            :step="1"
            :max="2"
            :min="0"
            show-ticks
            hide-details
            hide-track
            :tick-size="12"
            slider-class="!bg-rui-grey-200 dark:!bg-rui-grey-800"
            tick-class="!bg-rui-grey-200 dark:!bg-rui-grey-800"
            vertical
            @update:model-value="changeSelectedTheme($event)"
          />
          <div class="flex-1 flex flex-col-reverse justify-stretch -my-5 select-none">
            <div
              v-for="(label, index) in labels"
              :key="label"
              class="flex flex-col flex-1 justify-center pl-2 cursor-pointer text-rui-grey-500 dark:text-rui-grey-600 uppercase text-sm font-bold"
              :class="{ '!text-rui-primary dark:!text-rui-primary-lighter': selectedTheme === index }"
              @click="changeSelectedTheme(index)"
            >
              {{ label }}
            </div>
          </div>
        </label>
      </div>
    </RuiMenu>
    <RuiButton
      v-else
      variant="list"
      @click="toggleSelectedTheme()"
    >
      <template #prepend>
        <div class="relative">
          <RuiIcon
            v-if="darkModeEnabled"
            color="primary"
            name="lu-moon"
          />
          <RuiIcon
            v-else
            color="primary"
            name="lu-sun"
          />
          <div
            v-if="isAutomatic"
            class="absolute text-rui-primary -top-3 -right-1"
          >
            {{ automaticSymbol }}
          </div>
        </div>
      </template>
      <slot />
    </RuiButton>
  </div>
</template>
