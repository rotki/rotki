<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { usePrivacyMode } from '@/composables/privacy';
import { useScrambleSetting } from '@/composables/scramble-settings';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

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

const { persistPrivacySettings } = storeToRefs(useFrontendSettingsStore());

const {
  enabled,
  handleMultiplierUpdate,
  randomMultiplier,
  scrambleData,
  scrambleMultiplier,
} = useScrambleSetting();

const persistPrivacy = ref<boolean>(false);
const settingMenuOpen = ref<boolean>(false);

function setData() {
  set(persistPrivacy, get(persistPrivacySettings));
}

onMounted(setData);

watch(persistPrivacySettings, setData);
</script>

<template>
  <div class="relative">
    <RuiMenu
      v-model="showPrivacyModeMenu"
      data-cy="privacy-menu-content"
      menu-class="w-[22rem]"
      :popper="{ placement: 'bottom-end' }"
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
          :class="$style.expander"
          icon
          variant="text"
          v-bind="{ ...attrs, 'data-cy': 'privacy-menu' }"
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
          menu-class="w-[20rem]"
          :popper="{ placement: 'bottom-end' }"
          :close-on-content-click="false"
        >
          <template #activator="{ attrs }">
            <RuiButton
              variant="text"
              icon
              v-bind="attrs"
              data-cy="privacy-settings-menu"
            >
              <RuiIcon
                size="16"
                name="lu-settings"
              />
            </RuiButton>
          </template>
          <div class="p-4">
            <SettingsOption
              #default="{ updateImmediate: updatePersist }"
              setting="persistPrivacySettings"
              frontend-setting
            >
              <RuiSwitch
                v-model="persistPrivacy"
                color="primary"
                hide-details
                @update:model-value="updatePersist($event)"
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
            </SettingsOption>
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
          data-cy="privacy-mode-dropdown__input"
          :step="1"
          :max="2"
          :min="0"
          show-ticks
          hide-details
          :tick-size="12"
          slider-class="!bg-rui-grey-200 dark:!bg-rui-grey-800"
          tick-class="!bg-rui-grey-200 dark:!bg-rui-grey-800"
          vertical
          @update:model-value="changePrivacyMode($event)"
        />
        <div class="flex-1 flex flex-col-reverse justify-stretch -my-7 select-none">
          <div
            v-for="(label, index) in labels"
            :key="label.title"
            class="flex flex-col flex-1 justify-center gap-0.5 pl-4 cursor-pointer text-rui-grey-500 dark:text-rui-grey-600"
            :class="{ '!text-rui-primary dark:!text-rui-primary-lighter': privacyMode >= index }"
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
        <SettingsOption
          #default="{ updateImmediate: updateScramble }"
          :class="$style.scrambler__toggle"
          setting="scrambleData"
          frontend-setting
        >
          <RuiSwitch
            v-model="scrambleData"
            color="secondary"
            size="sm"
            data-cy="privacy-mode-scramble__toggle"
            hide-details
            @update:model-value="updateScramble($event)"
          >
            <span class="text-sm">
              {{ t('user_dropdown.change_privacy_mode.scramble.label') }}
            </span>
          </RuiSwitch>
        </SettingsOption>

        <AmountInput
          v-model="scrambleMultiplier"
          :label="t('frontend_settings.scramble.multiplier.label')"
          :disabled="!scrambleData"
          variant="outlined"
          color="secondary"
          data-cy="privacy-mode-scramble__multiplier"
          hide-details
          dense
          @update:model-value="handleMultiplierUpdate($event)"
        >
          <template #append>
            <RuiButton
              :disabled="!scrambleData"
              variant="text"
              type="button"
              class="-mr-2 !p-2"
              data-cy="privacy-mode-scramble__random-multiplier"
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

<style module lang="scss">
.expander {
  @apply p-0 z-10 right-0 text-black top-[1.875rem] w-4 h-4 lg:top-8 lg:w-[1.125rem] lg:h-[1.125rem];
  @apply bg-rui-grey-100 absolute #{!important};
}

.scrambler {
  &__toggle {
    @apply bg-rui-secondary border border-rui-secondary text-white px-2 rounded-l pt-[1px] -mt-[1px];
  }
}

:global(.dark) {
  .expander {
    @apply text-white bg-black #{!important};
  }
}
</style>
