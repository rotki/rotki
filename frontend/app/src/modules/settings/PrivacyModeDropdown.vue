<script setup lang="ts">
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { usePrivacyMode } from '@/modules/settings/use-privacy';
import { useScrambleSetting } from '@/modules/settings/use-scramble-settings';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';

const { t } = useI18n({ useScope: 'global' });

const isDemo = import.meta.env.VITE_DEMO_MODE !== undefined;

const { showPrivacyModeMenu } = storeToRefs(useAreaVisibilityStore());

const labels = [
  {
    description: t('user_dropdown.change_privacy_mode.normal_mode.description'),
    title: t('user_dropdown.change_privacy_mode.normal_mode.label'),
  },
  {
    description: t('user_dropdown.change_privacy_mode.semi_private_mode.description'),
    title: t('user_dropdown.change_privacy_mode.semi_private_mode.label'),
  },
  {
    description: t('user_dropdown.change_privacy_mode.private_mode.description'),
    title: t('user_dropdown.change_privacy_mode.private_mode.label'),
  },
];

const { changePrivacyMode, privacyMode, privacyModeIcon, togglePrivacyMode } = usePrivacyMode();

const { model: persistPrivacy } = useSettingModel('persistPrivacySettings');
const { flush: flushScramble, model: scrambleModel } = useSettingModel('scrambleData');

const {
  enabled,
  handleMultiplierUpdate,
  randomMultiplier,
  modelScrambleData,
  modelScrambleMultiplier,
} = useScrambleSetting();

const settingMenuOpen = ref<boolean>(false);

async function updateScramble(value: boolean): Promise<void> {
  set(scrambleModel, value);
  await flushScramble();
}
</script>

<template>
  <div class="relative">
    <RuiMenu
      v-model="showPrivacyModeMenu"
      data-testid="privacy-menu-content"
      :class-names="{ menu: 'w-[22rem]' }"
      :options="{ placement: 'bottom-end' }"
      :persistent="settingMenuOpen"
    >
      <template #activator="{ attrs }">
        <MenuTooltipButton
          :tooltip="t('user_dropdown.change_privacy_mode.label')"
          class-name="privacy-mode-dropdown"
          @click="togglePrivacyMode()"
        >
          <RuiBadge
            :model-value="enabled && !isDemo"
            color="error"
            dot
            placement="top"
            offset-y="4"
            size="lg"
            class="flex items-center"
          >
            <RuiIcon :name="privacyModeIcon" />
          </RuiBadge>
        </MenuTooltipButton>
        <RuiButton
          class="p-0 z-10 right-0 text-black top-[1.875rem] w-4 h-4 lg:top-8 lg:w-[1.125rem] lg:h-[1.125rem] !bg-rui-grey-100 !absolute dark:text-white dark:!bg-black"
          icon
          variant="text"
          v-bind="{ ...attrs, 'data-testid': 'privacy-menu' }"
          size="sm"
        >
          <RuiIcon
            size="16"
            name="lu-chevron-down"
          />
        </RuiButton>
      </template>
      <div class="absolute right-4 top-4">
        <RuiMenu
          v-model="settingMenuOpen"
          :class-names="{ menu: 'w-[20rem]' }"
          :options="{ placement: 'bottom-end' }"
          :close-on-content-click="false"
        >
          <template #activator="{ attrs }">
            <RuiButton
              variant="text"
              icon
              v-bind="attrs"
              data-testid="privacy-settings-menu"
            >
              <RuiIcon
                size="16"
                name="lu-settings"
              />
            </RuiButton>
          </template>
          <div class="p-4">
            <RuiSwitch
              v-model="persistPrivacy"
              color="primary"
              hide-details
            >
              <div class="flex flex-col gap-1">
                <span class="text-sm">
                  {{ t('frontend_settings.persist_privacy.label') }}
                </span>
                <span class="text-xs text-rui-text-secondary">
                  {{ t('frontend_settings.persist_privacy.hint') }}
                </span>
              </div>
            </RuiSwitch>
          </div>
        </RuiMenu>
      </div>
      <label
        class="px-4 py-8 flex"
        for="privacy-mode-slider"
      >
        <RuiSlider
          id="privacy-mode-slider"
          :model-value="privacyMode"
          class="h-40 w-8"
          data-testid="privacy-mode-dropdown-input"
          :step="1"
          :max="2"
          :min="0"
          show-ticks
          hide-details
          :tick-size="12"
          :class-names="{
            slider: '!bg-rui-grey-200 dark:!bg-rui-grey-800',
            tick: '!bg-rui-grey-200 dark:!bg-rui-grey-800',
          }"
          vertical
          @update:model-value="changePrivacyMode($event)"
        />
        <div class="flex-1 flex flex-col-reverse justify-stretch -my-7 select-none">
          <div
            v-for="(label, index) in labels"
            :key="label.title"
            class="flex flex-col flex-1 justify-center gap-0.5 pl-4 cursor-pointer text-rui-grey-500 dark:text-rui-grey-600"
            :class="{ '!text-rui-primary dark:!text-rui-primary-lighter': privacyMode >= index }"
            data-testid="privacy-mode-option"
            :data-mode="index"
            @click="changePrivacyMode(index)"
          >
            <div class="uppercase text-sm font-bold">
              {{ label.title }}
            </div>
            <div class="text-xs">
              {{ label.description }}
            </div>
          </div>
        </div>
      </label>
      <div class="border-t border-default p-4 flex flex-col gap-4">
        <RuiSwitch
          v-model="modelScrambleData"
          color="secondary"
          size="sm"
          data-testid="privacy-mode-scramble-toggle"
          hide-details
          @update:model-value="updateScramble($event)"
        >
          <span class="text-sm">
            {{ t('user_dropdown.change_privacy_mode.scramble.label') }}
          </span>
        </RuiSwitch>

        <AmountInput
          v-model="modelScrambleMultiplier"
          :label="t('frontend_settings.scramble.multiplier.label')"
          :disabled="!modelScrambleData"
          variant="outlined"
          color="secondary"
          data-testid="privacy-mode-scramble-multiplier"
          hide-details
          dense
          @update:model-value="handleMultiplierUpdate($event)"
        >
          <template #append>
            <RuiButton
              :disabled="!modelScrambleData"
              variant="text"
              type="button"
              class="-mr-2 !p-2"
              data-testid="privacy-mode-scramble-random-multiplier"
              icon
              @click="handleMultiplierUpdate(randomMultiplier())"
            >
              <RuiIcon name="lu-shuffle" />
            </RuiButton>
          </template>
        </AmountInput>
      </div>
    </RuiMenu>
  </div>
</template>
