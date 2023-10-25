<script setup lang="ts">
const { t } = useI18n();

const tickLabels: string[] = [
  t('user_dropdown.change_privacy_mode.normal_mode.label').toString(),
  t('user_dropdown.change_privacy_mode.semi_private_mode.label').toString(),
  t('user_dropdown.change_privacy_mode.private_mode.label').toString()
];

// TODO: Remove css variable for tick description in Vue3 and use State Driven Dynamic CSS
// https://v3.vuejs.org/api/sfc-style.html#state-driven-dynamic-css
const sliderWrapperStyle: Record<string, string> = {
  '--tick-description-3': `'${t(
    'user_dropdown.change_privacy_mode.normal_mode.description'
  ).toString()}'`,
  '--tick-description-2': `'${t(
    'user_dropdown.change_privacy_mode.semi_private_mode.description'
  ).toString()}'`,
  '--tick-description-1': `'${t(
    'user_dropdown.change_privacy_mode.private_mode.description'
  ).toString()}'`
};

const { privacyModeIcon, privacyMode, togglePrivacyMode, changePrivacyMode } =
  usePrivacyMode();

const { scrambleData: enabled, scrambleMultiplier: multiplier } = storeToRefs(
  useSessionSettingsStore()
);

const scrambleData = ref<boolean>(false);
const scrambleMultiplier = ref<string>('0');

const randomMultiplier = () => generateRandomScrambleMultiplier().toString();

const setData = () => {
  set(scrambleData, get(enabled));
  set(scrambleMultiplier, get(multiplier).toString());
};

onMounted(setData);

watch([enabled, multiplier], setData);
</script>

<template>
  <div class="privacy-mode-dropdown">
    <VMenu
      offset-y
      :max-width="360"
      :min-width="360"
      :close-on-content-click="false"
      content-class="privacy-mode-dropdown__menu"
    >
      <template #activator="{ on }">
        <MenuTooltipButton
          :tooltip="t('user_dropdown.change_privacy_mode.label')"
          class-name="privacy-mode-dropdown secondary--text text--lighten-4"
          @click="togglePrivacyMode()"
        >
          <RuiBadge
            :value="enabled"
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
        <VBtn
          data-cy="privacy-menu"
          class="privacy-mode-dropdown__expander pa-0"
          depressed
          fab
          x-small
          v-on="on"
        >
          <RuiIcon size="16" name="arrow-down-s-line" />
        </VBtn>
      </template>
      <VCard>
        <div class="slider-wrapper" :style="sliderWrapperStyle">
          <VSlider
            :value="privacyMode"
            data-cy="privacy-mode-dropdown__input"
            :class="`selected-${privacyMode}`"
            :tick-labels="tickLabels"
            :step="1"
            :max="2"
            :min="0"
            ticks="always"
            :tick-size="4"
            vertical
            @change="changePrivacyMode($event)"
          />
        </div>
        <div class="scrambler">
          <div
            class="w-full border-t border-black/[.12] dark:border-white/[.12] mb-4"
          />
          <div class="flex">
            <SettingsOption
              #default="{ update: updateScramble }"
              class="scrambler-toggle"
              setting="scrambleData"
              session-setting
            >
              <RuiCheckbox
                v-model="scrambleData"
                color="secondary"
                size="sm"
                data-cy="privacy-mode-scramble__toggle"
                hide-details
                @input="updateScramble($event)"
              >
                <span class="text-white">
                  {{ t('user_dropdown.change_privacy_mode.scramble.label') }}
                </span>
              </RuiCheckbox>
            </SettingsOption>

            <SettingsOption
              #default="{ update: updateMultiplier }"
              setting="scrambleMultiplier"
              class="scrambler-data"
              :error-message="t('frontend_settings.validation.scramble.error')"
              session-setting
            >
              <RuiTextField
                v-model="scrambleMultiplier"
                :label="t('frontend_settings.label.scramble_multiplier')"
                :disabled="!scrambleData"
                variant="outlined"
                color="secondary"
                min="0"
                step="0.01"
                type="number"
                data-cy="privacy-mode-scramble__multiplier"
                hide-details
                dense
                @input="updateMultiplier($event || 1)"
              >
                <template #append>
                  <RuiButton
                    :disabled="!scrambleData"
                    variant="text"
                    type="button"
                    class="-mr-2 !p-2"
                    data-cy="privacy-mode-scramble__random-multiplier"
                    icon
                    @click="updateMultiplier(randomMultiplier())"
                  >
                    <RuiIcon name="shuffle-line" />
                  </RuiButton>
                </template>
              </RuiTextField>
            </SettingsOption>
          </div>
        </div>
      </VCard>
    </VMenu>
  </div>
</template>

<style scoped lang="scss">
.privacy-mode-dropdown {
  position: relative;

  &__expander {
    width: 20px;
    height: 20px;
    top: 32px;
    background-color: #f5f5f5 !important;
    @apply p-0 absolute z-10 right-0 text-black;
  }

  &__menu {
    border-radius: 0.5rem;

    .slider-wrapper {
      .v-input {
        :deep(.v-slider) {
          .v-slider {
            &__track-container {
              width: 4px;
              left: 0;
            }

            &__track-background {
              &.primary {
                background: var(--v-rotki-light-grey-darken1) !important;
              }
            }

            &__ticks-container {
              left: 0;
            }

            &__tick {
              --color: var(--v-rotki-light-grey-darken2);
              width: 10px !important;
              height: 10px !important;
              left: calc(50% - 5px) !important;
              border-radius: 50%;
              background-color: var(--color) !important;
              cursor: pointer;

              &-label {
                left: 30px !important;
                text-transform: uppercase;
                font-weight: bold;
                font-size: 0.75rem;
                color: var(--color);
                text-align: left;
                margin-top: 5px;

                &:after {
                  text-transform: none;
                  font-weight: normal;
                  display: block;
                }
              }

              @for $i from 1 through 3 {
                &:nth-child(#{$i}) {
                  bottom: calc(150% - (50% * #{$i}) - 5px) !important;

                  /* stylelint-disable selector-class-pattern */

                  .v-slider {
                    &__tick-label {
                      &::after {
                        content: var(--tick-description-#{$i});
                      }
                    }
                  }
                  /* stylelint-enable selector-class-pattern */
                }
              }
            }

            &__thumb-container {
              right: auto !important;
              left: 0;
            }

            &__thumb {
              &::before {
                transform: scale(1) !important;
              }
            }
          }
        }

        /* stylelint-disable plugin/stylelint-bem-namics */
        @for $i from 0 through 2 {
          &.selected-#{$i} {
            :deep(.v-slider) {
              .v-slider {
                &__tick {
                  @for $j from 3 - $i through 3 {
                    &:nth-child(#{$j}) {
                      --color: var(--v-primary-base);
                    }
                  }
                }
              }
            }
          }
        }
        /* stylelint-enable plugin/stylelint-bem-namics */
      }

      @apply p-8;
    }

    .scrambler {
      &-toggle {
        :deep(svg) {
          @apply text-white;
        }

        @apply bg-rui-secondary border border-rui-secondary text-white px-2 rounded-l;
      }

      &-data {
        :deep(fieldset) {
          @apply rounded-l-none;
        }
      }

      @apply px-4 mb-4;
    }
  }
}

.theme {
  &--dark {
    .privacy-mode-dropdown {
      &__expander {
        color: white !important;
        background: black !important;
      }

      &__menu {
        .slider-wrapper {
          .v-input {
            :deep(.v-slider) {
              .v-slider {
                &__tick {
                  --color: var(--v-secondary-lighten2);
                }
              }
            }
          }
        }
      }
    }
  }
}
</style>
