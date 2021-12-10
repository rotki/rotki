<template>
  <div>
    <v-menu
      id="user-dropdown"
      content-class="user-dropdown__menu"
      transition="slide-y-transition"
      max-width="250px"
      offset-y
    >
      <template #activator="{ on }">
        <menu-tooltip-button
          tooltip="Account"
          class-name="user-dropdown secondary--text text--lighten-2"
          :on-menu="on"
        >
          <v-icon>mdi-account-circle</v-icon>
        </menu-tooltip-button>
      </template>
      <v-list data-cy="user-dropdown">
        <v-list-item key="username" class="user-username">
          <v-list-item-title class="font-weight-bold text-center">
            {{ username }}
          </v-list-item-title>
        </v-list-item>
        <v-divider class="mx-4" />
        <v-list-item
          key="settings"
          class="user-dropdown__settings"
          to="/settings/general"
        >
          <v-list-item-avatar>
            <v-icon color="primary">mdi-cog</v-icon>
          </v-list-item-avatar>
          <v-list-item-title>
            {{ $t('user_dropdown.settings') }}
          </v-list-item-title>
        </v-list-item>
        <v-menu
          offset-x
          left
          :max-width="400"
          :close-on-content-click="false"
          content-class="user-dropdown__privacy-mode__menu"
        >
          <template #activator="{ on, attrs }">
            <v-list-item
              key="privacy-mode"
              data-cy="user-dropdown__privacy-mode"
              class="user-dropdown__privacy-mode"
              v-bind="attrs"
              v-on="on"
            >
              <v-list-item-avatar>
                <v-icon v-if="privacyMode" color="primary">mdi-eye-off</v-icon>
                <v-icon v-else color="primary">mdi-eye</v-icon>
              </v-list-item-avatar>
              <v-list-item-title>
                {{ $t('user_dropdown.change_privacy_mode.label') }}
              </v-list-item-title>
            </v-list-item>
          </template>
          <v-card>
            <div class="slider-wrapper pa-8" :style="sliderWrapperStyle">
              <v-slider
                :value="privacyMode"
                data-cy="user-dropdown__privacy-mode__input"
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

        <v-divider class="mx-4" />
        <v-list-item
          key="logout"
          class="user-dropdown__logout"
          @click="confirmLogout = true"
        >
          <v-list-item-avatar>
            <v-icon color="primary">mdi-logout-variant</v-icon>
          </v-list-item-avatar>
          <v-list-item-title>
            {{ $t('user_dropdown.logout') }}
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
    <confirm-dialog
      :display="confirmLogout"
      :title="$t('user_dropdown.confirmation.title')"
      :message="$t('user_dropdown.confirmation.message')"
      @confirm="logout()"
      @cancel="confirmLogout = false"
    />
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

@Component({
  components: {
    ConfirmDialog,
    MenuTooltipButton
  },
  computed: {
    ...mapState('session', ['privacyMode', 'username'])
  }
})
export default class UserDropdown extends Vue {
  privacyMode!: number;
  confirmLogout: boolean = false;

  changePrivacyMode(privacyMode: number) {
    this.$store.commit('session/privacyMode', privacyMode);
  }

  tickLabels: string[] = [
    this.$t('user_dropdown.change_privacy_mode.normal_mode.label').toString(),
    this.$t(
      'user_dropdown.change_privacy_mode.semi_private_mode.label'
    ).toString(),
    this.$t('user_dropdown.change_privacy_mode.private_mode.label').toString()
  ];

  // TODO: Remove css variable for tick description in Vue3 and use State Driven Dynamic CSS
  // https://v3.vuejs.org/api/sfc-style.html#state-driven-dynamic-css
  get sliderWrapperStyle() {
    return {
      '--tick-description-3': `'${this.$t(
        'user_dropdown.change_privacy_mode.normal_mode.description'
      ).toString()}'`,
      '--tick-description-2': `'${this.$t(
        'user_dropdown.change_privacy_mode.semi_private_mode.description'
      ).toString()}'`,
      '--tick-description-1': `'${this.$t(
        'user_dropdown.change_privacy_mode.private_mode.description'
      ).toString()}'`
    };
  }

  async logout() {
    this.confirmLogout = false;
    const { dispatch } = this.$store;

    await dispatch('session/logout');
    if (this.$route.path !== '/') {
      await this.$router.replace('/');
    }
  }
}
</script>

<style scoped lang="scss">
.user-dropdown {
  &__privacy-mode {
    &__menu {
      .slider-wrapper {
        .v-input {
          ::v-deep {
            .v-slider {
              width: 210px;

              &__track-container {
                width: 4px;
                left: auto !important;
                right: 0;
                transform: translateX(50%) !important;
              }

              &__track-background {
                &.primary {
                  background: var(--v-rotki-light-grey-darken1) !important;
                }
              }

              &__ticks-container {
                left: auto !important;
                right: 0;
                transform: translateX(50%) !important;
              }

              &__tick {
                --color: var(--v-rotki-light-grey-darken2);
                width: 10px !important;
                height: 10px !important;
                right: calc(50% - 5px) !important;
                border-radius: 50%;
                background-color: var(--color) !important;
                cursor: pointer;

                &-label {
                  left: auto !important;
                  right: 30px;
                  text-transform: uppercase;
                  font-weight: bold;
                  font-size: 0.75rem;
                  color: var(--color);
                  text-align: right;
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
                left: auto !important;
                right: 0;
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
}

.theme {
  &--dark {
    .user-dropdown {
      &__privacy-mode {
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
}
</style>
