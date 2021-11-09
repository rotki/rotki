<template>
  <full-size-content>
    <div :class="$style.content">
      <v-col cols="12">
        <v-row
          v-if="progress"
          align="center"
          justify="center"
          class="font-weight-light"
          :class="$style.percentage"
          v-text="$t('progress_screen.progress', { progress: percentage })"
        />
        <v-row align="center" justify="center" :class="$style.loader">
          <v-col cols="10">
            <v-progress-linear
              v-if="progress"
              class="text-center"
              rounded
              height="16"
              color="primary"
              :value="progress"
            />
            <div v-else :class="$style.indeterminate">
              <v-progress-circular
                rounded
                indeterminate
                :size="70"
                color="primary"
              />
            </div>
          </v-col>
        </v-row>
        <v-row align="center" justify="center">
          <p class="text-center font-weight-light" :class="$style.description">
            <slot name="message" />
          </p>
        </v-row>
        <v-row align="center" justify="center">
          <v-col cols="4">
            <v-divider />
          </v-col>
        </v-row>
        <v-row align="center" justify="center" :class="$style.warning">
          <div class="font-weight-light text-subtitle-2">
            <slot />
          </div>
        </v-row>
      </v-col>
    </div>
  </full-size-content>
</template>
<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import FullSizeContent from '@/components/common/FullSizeContent.vue';

export default defineComponent({
  name: 'ProgressScreen',
  components: { FullSizeContent },
  props: {
    progress: { required: false, default: '', type: String }
  },
  setup(props) {
    const { progress } = toRefs(props);
    const percentage = computed(() => {
      const currentProgress = progress.value;
      try {
        const number = parseFloat(currentProgress);
        return number.toFixed(2);
      } catch (e: any) {
        return currentProgress;
      }
    });
    return {
      percentage
    };
  }
});
</script>
<style module lang="scss">
.indeterminate {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-bottom: 80px;
}

.content {
  display: flex;
  align-items: center;
  flex-direction: row;
  height: 100%;
  width: 100%;
}

.loader {
  min-height: 80px;
}

.percentage {
  font-size: 46px;
}

.description {
  font-size: 16px;
}

.warning {
  margin-top: 30px;
}
</style>
