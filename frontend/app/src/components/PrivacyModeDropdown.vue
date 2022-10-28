<template>
  <div class="privacy-mode-dropdown">
    <v-menu
      offset-y
      :max-width="300"
      :min-width="300"
      :close-on-content-click="false"
      content-class="privacy-mode-dropdown__menu"
    >
      <template #activator="{ on }">
        <menu-tooltip-button
          :tooltip="tc('user_dropdown.change_privacy_mode.label')"
          class-name="privacy-mode-dropdown secondary--text text--lighten-4"
          @click="togglePrivacyMode"
        >
          <v-icon>{{ privacyModeIcon }}</v-icon>
        </menu-tooltip-button>
        <v-btn
          data-cy="privacy-menu"
          class="privacy-mode-dropdown__expander pa-0"
          depressed
          fab
          x-small
          v-on="on"
        >
          <v-icon>mdi-chevron-down</v-icon>
        </v-btn>
      </template>
      <v-card>
        <div class="slider-wrapper pa-8" :style="sliderWrapperStyle">
          <v-slider
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
      </v-card>
    </v-menu>
  </div>
</template>

<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { usePrivacyMode } from '@/composables/privacy';

const { t, tc } = useI18n();

const tickLabels: string[] = [
  t('user_dropdown.change_privacy_mode.normal_mode.label').toString(),
  t('user_dropdown.change_privacy_mode.semi_private_mode.label').toString(),
  t('user_dropdown.change_privacy_mode.private_mode.label').toString()
];

// TODO: Remove css variable for tick description in Vue3 and use State Driven Dynamic CSS
// https://v3.vuejs.org/api/sfc-style.html#state-driven-dynamic-css
const sliderWrapperStyle: { [key: string]: string } = {
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
</script>
<style scoped lang="scss">
.privacy-mode-dropdown {
  position: relative;

  &__expander {
    position: absolute;
    z-index: 1;
    width: 20px;
    height: 20px;
    top: 32px;
    right: 0;
    color: black;
    background-color: #f5f5f5 !important;
  }

  &__menu {
    border-radius: 0.5rem;

    .slider-wrapper {
      .v-input {
        :deep() {
          .v-slider {
            width: 210px;

            &__track-container {
              width: 4px;
              right: auto !important;
              left: 0;
              transform: translateX(-50%) !important;
            }

            &__track-background {
              &.primary {
                background: var(--v-rotki-light-grey-darken1) !important;
              }
            }

            &__ticks-container {
              right: auto !important;
              left: 0;
              transform: translateX(-50%) !important;
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

                  /* stylelint-disable selector-class-pattern, rule-empty-line-before */
                  .v-slider {
                    &__tick-label {
                      &::after {
                        content: var(--tick-description-#{$i});
                      }
                    }
                  }
                  /* stylelint-enable selector-class-pattern, rule-empty-line-before */
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

        /* stylelint-disable plugin/stylelint-bem-namics, rule-empty-line-before */
        @for $i from 0 through 2 {
          &.selected-#{$i} {
            :deep() {
              .v-slider {
                &__tick {
                  @for $j from 3-$i through 3 {
                    &:nth-child(#{$j}) {
                      --color: var(--v-primary-base);
                    }
                  }
                }
              }
            }
          }
        }
        /* stylelint-enable plugin/stylelint-bem-namics, rule-empty-line-before */
      }
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
            :deep() {
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
