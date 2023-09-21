<script lang="ts" setup>
import { type Ref } from 'vue';
import AmountInput from '@/components/inputs/AmountInput.vue';

withDefaults(
  defineProps<{
    primaryValue: string;
    secondaryValue: string;
    label: { primary?: string; secondary?: string };
    errorMessages?: {
      primary?: Record<string, string | string[]>;
      secondary?: Record<string, string | string[]>;
    };
    loading?: boolean;
  }>(),
  {
    label: () => ({}),
    errorMessages: () => ({}),
    loading: false
  }
);

const emit = defineEmits<{
  (e: 'update:primary-value', value: string): void;
  (e: 'update:secondary-value', value: string): void;
  (e: 'update:reversed', reversed: boolean): void;
}>();

const reversed: Ref<boolean> = ref(false);

const rootAttrs = useAttrs();

const reverse = () => {
  const newReversed = !get(reversed);
  set(reversed, newReversed);
  emit('update:reversed', newReversed);

  nextTick(() => {
    if (!newReversed) {
      get(primaryInput)?.focus();
    } else {
      get(secondaryInput)?.focus();
    }
  });
};

const primaryInput: Ref<InstanceType<typeof AmountInput> | null> = ref(null);
const secondaryInput: Ref<InstanceType<typeof AmountInput> | null> = ref(null);

const updatePrimaryValue = (value: string) => {
  emit('update:primary-value', value);
};

const updateSecondaryValue = (value: string) => {
  emit('update:secondary-value', value);
};
</script>

<template>
  <div
    class="wrapper flex"
    :class="{
      'flex-column': !reversed,
      'flex-column-reverse': reversed
    }"
  >
    <AmountInput
      ref="primaryInput"
      :value="primaryValue"
      :disabled="reversed || rootAttrs.disabled"
      :hide-details="reversed"
      filled
      persistent-hint
      data-cy="primary"
      :class="`${!reversed ? 'v-input--is-enabled' : ''}`"
      v-bind="rootAttrs"
      :label="label.primary"
      :error-messages="errorMessages.primary"
      :loading="!reversed && loading"
      @input="updatePrimaryValue($event)"
    />

    <AmountInput
      ref="secondaryInput"
      :value="secondaryValue"
      :disabled="!reversed || rootAttrs.disabled"
      :hide-details="!reversed"
      filled
      persistent-hint
      data-cy="secondary"
      :class="`${reversed ? 'v-input--is-enabled' : ''}`"
      v-bind="rootAttrs"
      :label="label.secondary"
      :error-messages="errorMessages.secondary"
      :loading="reversed && loading"
      @input="updateSecondaryValue($event)"
    />

    <VBtn
      class="swap-button"
      fab
      small
      dark
      color="primary"
      data-cy="grouped-amount-input__swap-button"
      @click="reverse()"
    >
      <VIcon>mdi-swap-vertical</VIcon>
    </VBtn>
  </div>
</template>

<style scoped lang="scss">
.wrapper {
  position: relative;

  :deep(.v-input) {
    position: static;

    .v-input {
      &__slot {
        margin-bottom: 0;
        background: transparent !important;
      }
    }

    &.v-input {
      &--is-disabled {
        .v-input {
          &__control {
            .v-input {
              &__slot {
                &::before {
                  content: none;
                }
              }
            }
          }
        }
      }

      &--is-enabled {
        &::before {
          content: '';
          width: 100%;
          height: 100%;
          position: absolute;
          top: 0;
          left: 0;
          border: 1px solid rgba(0, 0, 0, 0.42);
          border-radius: 4px;
        }

        &.v-input {
          &--is-focused {
            &::before {
              border: 2px solid var(--v-primary-base) !important;
            }
          }
        }

        &.error {
          &--text {
            &::before {
              border: 2px solid var(--v-error-base) !important;
            }
          }
        }
      }
    }

    .v-text-field {
      &__details {
        position: absolute;
        bottom: -30px;
        width: 100%;
      }
    }
  }
}

.swap-button {
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
}

.theme {
  &--dark {
    .wrapper {
      /* stylelint-disable selector-class-pattern,selector-nested-pattern */

      :deep(.v-input--is-enabled),
      :deep(.v-input__slot) {
        &::before {
          border-color: hsla(0, 0%, 100%, 0.24);
        }
      }
      /* stylelint-enable selector-class-pattern,selector-nested-pattern */
    }
  }
}
</style>
