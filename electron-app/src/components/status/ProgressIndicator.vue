<template>
  <v-menu id="notification-indicator" transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-badge>
        <v-btn color="primary" dark icon text v-on="on">
          <v-icon v-if="hasRunningTasks" class="top-loading-icon">
            fa fa-circle-o-notch fa-spin
          </v-icon>
          <v-icon v-else>
            fa fa-check-circle
          </v-icon>
        </v-btn>
      </v-badge>
    </template>
    <v-row class="progress-indicator__details">
      <v-col v-if="tasks.length > 0">
        <v-list two-line>
          <template v-for="task in tasks">
            <v-list-item :key="task.id" class="progress-indicator__task">
              <v-list-item-content>
                <v-list-item-title
                  v-text="task.description"
                ></v-list-item-title>
                <v-progress-linear
                  v-if="task.type !== 'process_trade_history'"
                  indeterminate
                  class="progress-indicator__task__progress"
                ></v-progress-linear>
                <v-progress-linear
                  v-else
                  :value="progress"
                  class="progress-indicator__task__progress"
                ></v-progress-linear>
              </v-list-item-content>
            </v-list-item>
            <v-divider :key="task.id"></v-divider>
          </template>
        </v-list>
      </v-col>
      <v-col v-else class="progress-indicator__no_tasks align justify">
        <v-icon color="primary">fa fa-info-circle</v-icon>
        <div>No running tasks</div>
      </v-col>
    </v-row>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { Task } from '@/model/task';

const { mapGetters } = createNamespacedHelpers('tasks');
const mapReportGetters = createNamespacedHelpers('reports').mapGetters;

@Component({
  computed: {
    ...mapGetters(['hasRunningTasks', 'tasks']),
    ...mapReportGetters(['progress'])
  }
})
export default class ProgressIndicator extends Vue {
  hasRunningTasks!: boolean;
  tasks!: Task[];
  progress!: number;
}
</script>

<style scoped lang="scss">
.progress-indicator__details {
  width: 300px;
  height: 350px;
  background-color: white;
}

.progress-indicator__no_tasks {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.progress-indicator__task {
  min-height: 35px;
}

.progress-indicator__task__progress {
  margin-top: 8px;
}
</style>
