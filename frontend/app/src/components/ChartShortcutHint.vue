<template>
  <div>
    <v-dialog width="250">
      <template #activator="{ on }">
        <v-btn depressed x-small class="hint__activator" v-on="on">
          <v-icon>mdi-magnify-plus-outline</v-icon>
        </v-btn>
      </template>
      <div>
        <card>
          <template #title>{{ $t('chart.hint.title') }}</template>
          <div class="shortcut">
            <div class="shortcut__title">
              {{ $t('chart.hint.labels.zoom_in') }}
            </div>
            <div class="shortcut__buttons">
              <div>{{ modifier }}</div>
              <div>{{ $t('chart.hint.key.wheel_up') }}</div>
            </div>
          </div>
          <div class="shortcut">
            <div class="shortcut__title">
              {{ $t('chart.hint.labels.zoom_out') }}
            </div>
            <div class="shortcut__buttons">
              <div>{{ modifier }}</div>
              <div>{{ $t('chart.hint.key.wheel_down') }}</div>
            </div>
          </div>
          <div class="shortcut">
            <div class="shortcut__title">
              {{ $t('chart.hint.labels.reset_zoom') }}
            </div>
            <div class="shortcut__buttons">
              <div>{{ $t('chart.hint.key.double_click') }}</div>
            </div>
          </div>
        </card>
      </div>
    </v-dialog>
  </div>
</template>
<script lang="ts">
import {
  computed,
  defineComponent,
  onBeforeMount,
  ref
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { interop } from '@/electron-interop';

export default defineComponent({
  name: 'ChartShortcutHint',
  setup() {
    const isMac = ref<boolean>(false);
    const modifier = computed<string>(() => (get(isMac) ? 'Cmd' : 'Ctrl'));

    onBeforeMount(async () => {
      set(isMac, await interop.isMac());
    });

    return {
      modifier
    };
  }
});
</script>
<style scoped lang="scss">
.hint {
  &__activator {
    width: 30px;
    height: 30px !important;
    color: black;
    background-color: #f5f5f5 !important;
  }
}

.shortcut {
  margin-bottom: 1rem;

  &__title {
    margin-bottom: 0.25rem;
  }

  &__buttons {
    display: flex;

    div {
      font-weight: bold;
      font-size: 0.875rem;
      padding: 0 0.5rem;
      text-transform: uppercase;
      background: var(--v-rotki-grey-lighten2);
      border-bottom: 4px solid var(--v-rotki-grey-lighten1);
      border-radius: 4px;

      &:not(:first-child) {
        margin-left: 0.5rem;
      }
    }
  }
}

.theme {
  &--dark {
    .hint {
      &__activator {
        color: white !important;
        background: black !important;
      }
    }

    .shortcut {
      &__buttons {
        div {
          background: var(--v-rotki-light-grey-lighten2);
          border-bottom: 4px solid var(--v-rotki-light-grey-lighten3);
        }
      }
    }
  }
}
</style>
