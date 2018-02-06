require("./zerorpc_client.js")();

let callbacks = [];
let tasks_map = {};

function Task (task_id, task_type) {
    this.id = task_id;
    this.type = task_type;
}

function add_task_dropdown(task_id, task_description) {
    var str='<li class="task'+task_id+'"><a href="#"><div><p><strong>' + task_description + '</strong><span class="pull-right text-muted">40% Complete</span></p><div class="progress progress-striped active"><div class="progress-bar progress-bar-success" role="progressbar" aria-valuenow="40" aria-valuemin="0" aria-valuemax="100" style="width: 40%"><span class="sr-only">40% Complete (success)</span></div></div></div></a></li><li class="divider task'+task_id+'"></li>';
    $(str).appendTo($(".dropdown-tasks"));
}

function create_task(task_id, type, description) {
    tasks_map[task_id] = new Task(task_id, type);
    add_task_dropdown(task_id, description);
}

function remove_task(task_id) {
    delete tasks_map[task_id];
    $('.task'+task_id).remove();
}

function monitor_add_callback(task_type, cb) {
    callbacks.push([task_type, cb]);
}

function monitor_tasks() {
    if (Object.keys(tasks_map).length == 0) {
        // if we get here it means we finished all jobs
        $('#top-loading-icon').removeClass().addClass('fa fa-check-circle fa-fw');
        return;
    }

    // else it means we still need to have data to load
    $('#top-loading-icon').removeClass().addClass('fa fa-circle-o-notch fa-spin fa-fw');

    for (var task_id in tasks_map) {
        let task = tasks_map[task_id];
        if (task.id == null) {
            console.log('NULL TASK ID: ' + JSON.stringify(task, null, 4));
            continue;
        }

        client.invoke("query_task_result", task.id, function (error, res) {
            console.log("monitor_tasks. Querying task " + task.id);
            if (res != null) {
                for (let i = 0; i < callbacks.length; i++) {
                    if (task.type == callbacks[i][0]) {
                        callbacks[i][1](res);
                        remove_task(task.id);
                        return;
                    }
                }
                // if we get here we got a result for which there was no handler
                console.log("No handler found for task '" + task.type +"' with id " + task.id);
            }
        });

    }
}


function init_monitor() {
    // monitor tasks every 2 seconds
    setInterval(monitor_tasks, 2000);
}

module.exports = function() {
    this.init_monitor = init_monitor;
    this.monitor_add_callback = monitor_add_callback;
    this.create_task = create_task;
};
