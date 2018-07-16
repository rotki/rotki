require("./zerorpc_client.js")();

let callbacks = [];
let tasks_map = {};
let balance_tasks = [];
var BalanceStatus = Object.freeze({'start':1, "requested":2, "complete":3});
let balance_query_status = BalanceStatus.start;

function Task (task_id, task_type, expect_callback) {
    this.id = task_id;
    this.type = task_type;
    this.should_expect_callback = expect_callback;
}

function add_task_dropdown(task_id, task_description) {
    var str='<li class="task'+task_id+'"><a href="#"><div><p><strong>' + task_description + '</strong><span class="pull-right text-muted">40% Complete</span></p><div class="progress progress-striped active"><div class="progress-bar progress-bar-success" role="progressbar" aria-valuenow="40" aria-valuemin="0" aria-valuemax="100" style="width: 40%"><span class="sr-only">40% Complete (success)</span></div></div></div></a></li><li class="divider task'+task_id+'"></li>';
    $(str).appendTo($(".dropdown-tasks"));
}

/**
 * Creates an asynchronous monitoring task for which we are going to be continuously querying the backend
 * @param task_id[int] A numerical id for the task
 * @param type[str] The task type. This determines which callback will be run at task completion
 * @param description[str] A description for the task
 * @param is_balance_task[bool] A boolean to determine if the task is part of the periodic balance query.
 *                              If yes, at the end of all such queries the result will be saved to the DB.
 * @param expect_callback[bool] A boolean to determine if the task should expect a callback to be registered for
*                               it or not.
*/
function create_task(task_id, type, description, is_balance_task, expect_callback) {
    tasks_map[task_id] = new Task(task_id, type, expect_callback);
    add_task_dropdown(task_id, description);
    if (is_balance_task) {
        balance_tasks.push(task_id);
        console.log('--> Adding Task ' + task_id + ' to balance_task');
        if (balance_query_status == BalanceStatus.start || balance_query_status == BalanceStatus.complete) {
            balance_query_status = BalanceStatus.requested;
            console.log('--> balance_query_status is now requested');
        }
    }
}

function remove_task(task_id) {
    // TODO: not the best way to do it complexity wise. Find better way
    // If the task is found in the balance tasks then remove it and if last task proceed to post query action
    for (let i = 0; i < balance_tasks.length; i++) {
        let task = balance_tasks[i];
        if (task == task_id) {
            if (balance_query_status != BalanceStatus.requested) {
                throw 'BalanceStatus should only be requested at this point. But value is' + balance_query_status;
            }
            balance_tasks.splice(i, 1);
            if (balance_tasks.length == 0) {
                balance_query_status = BalanceStatus.complete;
                // TODO: Perhaps this is not the best way to achieve the saving of the balances but it works
                // Essentially we re-request a query of all balances which should be very fast due to the cache
                // and that should take care of saving the data for us
                client.invoke('query_balances_async', (error, result) => {
                    if (error || result == null) {
                        console.log("Error at querying all balances asynchronously: " + error);
                        return;
                    }
                    create_task(
                        result['task_id'],
                        'query_balances',
                        'Query All Balances',
                        false,
                        false
                    );
                });
            }
            break;
        }
    }
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
            if (!task.should_expect_callback) {
                remove_task(task.id);
            } else {
                if (res != null) {
                    let handled = 0;
                    for (let i = 0; i < callbacks.length; i++) {
                        if (task.type == callbacks[i][0]) {
                            callbacks[i][1](res);
                            remove_task(task.id);
                            handled += 1;
                        }
                    }
                    if (handled == 0) {
                        console.log("No handler found for task '" + task.type +"' with id " + task.id);
                    }
                }
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
