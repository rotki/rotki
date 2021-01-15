<template>
  <div>
    <v-menu
      id="notification-indicator"
      transition="slide-y-transition"
      bottom
      max-height="360px"
      offset-y
    >
      <template #activator="{ on }">
        <menu-tooltip-button
          tooltip="Running Tasks"
          class-name="secondary--text text--lighten-2"
          :on-menu="on"
        >
          <v-icon v-if="hasRunningTasks" class="top-loading-icon">
            mdi-spin mdi-loading
          </v-icon>
          <v-icon v-else> mdi-check-circle </v-icon>
        </menu-tooltip-button>
      </template>
      <v-container class="progress-indicator__container">
        <v-row class="progress-indicator__details">
          <v-col v-if="tasks.length > 0">
            <v-list two-line>
              <template v-for="task in tasks">
                <v-list-item :key="task.id" class="progress-indicator__task">
                  <v-list-item-content>
                    <v-list-item-title v-text="task.meta.title" />
                    <v-list-item-subtitle
                      v-if="task.meta.description"
                      class="mt-1"
                      v-text="task.meta.description"
                    />
                    <v-progress-linear
                      v-if="task.type !== 'process_trade_history'"
                      indeterminate
                      class="progress-indicator__task__progress"
                    />
                    <v-progress-linear
                      v-else
                      :value="progress"
                      class="progress-indicator__task__progress"
                    />
                  </v-list-item-content>
                </v-list-item>
                <v-divider :key="`task-${task.id}`" />
              </template>
            </v-list>
          </v-col>
          <v-col v-else class="progress-indicator__no-tasks align justify">
            <v-icon color="primary">mdi-information</v-icon>
            <p
              class="progress-indicator__no-tasks__label"
              v-text="$t('progress_indicator.no_tasks')"
            />
          </v-col>
        </v-row>
      </v-container>
    </v-menu>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { Task, TaskMeta } from '@/model/task';

@Component({
  components: { MenuTooltipButton },
  computed: {
    ...mapGetters('tasks', ['hasRunningTasks', 'tasks']),
    ...mapGetters('reports', ['progress'])
  }
})
export default class ProgressIndicator extends Vue {
  hasRunningTasks!: boolean;
  tasks!: Task<TaskMeta>[];
  progress!: number;
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.progress-indicator {
  &__container {
    @extend .themed-scrollbar;
  }

  &__details {
    width: 350px;
    height: 350px;
    background-color: white;
  }

  &__no-tasks {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;

    &__label {
      font-size: 22px;
      margin-top: 22px;
      font-weight: 300;
      color: rgb(0, 0, 0, 0.6);
    }
  }

  &__task {
    min-height: 35px;

    &__progress {
      margin-top: 8px;
    }
  }
}
</style>
