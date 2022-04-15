<template>
  <div>
    <v-menu
      offset-y
      :max-width="300"
      :min-width="300"
      :close-on-content-click="false"
      content-class="privacy-mode-dropdown__menu"
    >
      <template #activator="{ on }">
        <menu-tooltip-button
          :tooltip="$t('user_dropdown.change_privacy_mode.label')"
          class-name="privacy-mode-dropdown secondary--text text--lighten-4"
          :on-menu="on"
        >
          <v-icon>{{ privacyModeIcon }}</v-icon>
        </menu-tooltip-button>
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

<script lang="ts">
import { computed, defineComponent } from '@vue/composition-api';
import { get } from '@vueuse/core';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { setupSession } from '@/composables/session';
import i18n from '@/i18n';

const tickLabels: string[] = [
  i18n.t('user_dropdown.change_privacy_mode.normal_mode.label').toString(),
  i18n
    .t('user_dropdown.change_privacy_mode.semi_private_mode.label')
    .toString(),
  i18n.t('user_dropdown.change_privacy_mode.private_mode.label').toString()
];

// TODO: Remove css variable for tick description in Vue3 and use State Driven Dynamic CSS
// https://v3.vuejs.org/api/sfc-style.html#state-driven-dynamic-css
const sliderWrapperStyle: { [key: string]: string } = {
  '--tick-description-3': `'${i18n
    .t('user_dropdown.change_privacy_mode.normal_mode.description')
    .toString()}'`,
  '--tick-description-2': `'${i18n
    .t('user_dropdown.change_privacy_mode.semi_private_mode.description')
    .toString()}'`,
  '--tick-description-1': `'${i18n
    .t('user_dropdown.change_privacy_mode.private_mode.description')
    .toString()}'`
};

export default defineComponent({
  name: 'PrivacyModeDropdown',
  components: {
    MenuTooltipButton
  },
  setup() {
    const { privacyMode, changePrivacyMode } = setupSession();

    const privacyModeIcon = computed<string>(() => {
      return ['mdi-eye', 'mdi-eye-minus', 'mdi-eye-off'][get(privacyMode)];
    });

    return {
      privacyModeIcon,
      privacyMode,
      changePrivacyMode,
      tickLabels,
      sliderWrapperStyle
    };
  }
});
</script>

<style scoped lang="scss">
.privacy-mode-dropdown {
  &__menu {
    .slider-wrapper {
      .v-input {
        ::v-deep {
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
            ::v-deep {
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
      &__menu {
        .slider-wrapper {
          .v-input {
            ::v-deep {
              .v-slider {
                &__tick {
                  --color: var(--v-secondary-lighten2);
                }
              }
            }

            /* stylelint-disable plugin/stylelint-bem-namics, rule-empty-line-before */
            @for $i from 0 through 2 {
              &.selected-#{$i} {
                ::v-deep {
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
  }
}
</style>
