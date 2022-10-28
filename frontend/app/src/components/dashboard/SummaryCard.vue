<template>
  <v-card
    :loading="isLoading"
    :class="`dashboard__summary-card__${name}`"
    class="pb-1"
  >
    <v-card-title
      class="font-weight-medium text-capitalize px-4 pt-3 pb-0 secondary--text summary-card__header"
    >
      <card-title>
        <navigator-link :enabled="!!navigatesTo" :to="{ path: navigatesTo }">
          {{ t('summary_card.title', { name }) }}
        </navigator-link>
      </card-title>
      <v-tooltip v-if="$slots.tooltip" bottom max-width="300px">
        <template #activator="{ on }">
          <v-icon
            small
            class="mb-3 ml-1 summary-card__header__tooltip"
            v-on="on"
          >
            mdi-information-circle
          </v-icon>
        </template>
        <div>
          <slot name="tooltip" />
        </div>
      </v-tooltip>
      <v-spacer />
      <span>
        <v-tooltip v-if="canRefresh" bottom max-width="300px">
          <template #activator="{ on }">
            <v-btn
              icon
              x-small
              :disabled="isLoading"
              color="primary"
              class="summary-card__refresh-icon"
              @click="refresh(name)"
              v-on="on"
            >
              <v-icon color="primary">mdi-refresh</v-icon>
            </v-btn>
          </template>
          <span>{{ t('summary_card.refresh_tooltip', { name }) }}</span>
        </v-tooltip>
      </span>
    </v-card-title>
    <v-list>
      <slot />
    </v-list>
  </v-card>
</template>

<script setup lang="ts">
const NavigatorLink = defineAsyncComponent(
  () => import('@/components/helper/NavigatorLink.vue')
);

defineProps({
  name: { required: true, type: String },
  isLoading: { required: false, type: Boolean, default: false },
  canRefresh: { required: false, type: Boolean, default: false },
  navigatesTo: { required: false, type: String, default: '' }
});

const emit = defineEmits(['refresh']);

const refresh = (balanceSource: string) => {
  emit('refresh', balanceSource.toLowerCase());
};

const { t } = useI18n();
</script>

<style scoped lang="scss">
.summary-card {
  .v-list-item {
    font-size: 0.8em;
    max-height: 48px;
  }

  &__refresh-icon {
    filter: grayscale(100%);
    padding: 1rem;

    &:hover {
      filter: grayscale(0);
    }
  }

  &__header {
    &__tooltip {
      visibility: hidden;
    }

    &:hover {
      .summary-card {
        &__header {
          &__tooltip {
            visibility: visible;
          }
        }
      }
    }
  }
}
</style>
