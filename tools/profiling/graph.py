"""
Module to plot profile data.

For memory time-line with memory usage and number of blocks through time you
can use the following command:

    python -m profiling memory timeline DATA_ROOT/*_memory.data

For the latency of sampling, you can use the following plot:

    python -m profiling latency scatter DATA_ROOT/*_memory.data

For visualizing the most common classes by count:

    python -m profiling memory objcount DATA_ROOT/*_objects.pickle

Flame graphs can be generated with Brendan Gregg's tool brendangregg/FlameGraph:

    cat DATA_ROOT/*_stack.data | flamegraph > flamegraph.svg

Sampling profiling will usually produce data for the same points (with the
exception of the objcount that is more coarse), so these plots can be combined
using ImageMagick:

    convert -append memory_timeline.png latency_scatter.png memory_objcount.png collage.png
"""

# Improvements:
# - Draw the composite graphs with matplotlib instead of using convert and make
#   sure to aling all the points
# - Add the option to filter the data for plotting, effectivelly allowing
#   zooming
import collections
import pickle
from datetime import datetime
from itertools import chain
from typing import Any, Dict, Optional

from .constants import INTERVAL_SECONDS, ONESECOND_TIMEDELTA

# column position in the data file
TIMESTAMP = 0
MEMORY = 1


def ts_to_dt(string_ts):
    """converts a string timestamp to a datatime object"""
    return datetime.fromtimestamp(int(float(string_ts)))


def plot_date_axis(axes):
    from matplotlib import dates

    date_fmt = dates.DateFormatter("%d/%b")
    hour_fmt = dates.DateFormatter("%H:%M")

    # TODO: set xaxis minor interval dynamically

    axes.xaxis.set_major_locator(dates.DayLocator(interval=1))
    axes.xaxis.set_major_formatter(date_fmt)
    # less than 5 days and interval of 3 is okay
    axes.xaxis.set_minor_locator(dates.HourLocator(interval=4))
    axes.xaxis.set_minor_formatter(hour_fmt)
    axes.xaxis.set_tick_params(which="major", pad=15)


def plot_configure(figure):
    figure.set_figwidth(18)
    figure.set_figheight(4.5)


def memory_objcount(output, data_list, topn=10):
    import matplotlib.pyplot as plt

    # make sure we are sorted by timestamp
    data_list = sorted(data_list, key=lambda el: el[0][TIMESTAMP])

    # some classes might appear in one sample but not in another, we need to
    # make sure that this class will have all points otherwise the matplotlib
    # call will fail
    alltime_count = sum(len(data) for data in data_list)
    # extra points points to create the valleys in the graph
    alltime_count += len(data_list) * 2
    alltime_factory = lambda: [0.0 for __ in range(alltime_count)]

    position = 0
    alltime_data: Dict = {}
    alltime_timestamps = []
    for data in data_list:
        sample_highcount: Dict = {}

        # some classes might not appear on all samples, nevertheless the list
        # must have the same length
        sample_count = len(data)
        sample_factory = lambda: [0.0 for __ in range(sample_count)]
        objcount: Dict = collections.defaultdict(sample_factory)

        # group the samples by class
        for index, (__, count_per_type) in enumerate(data):
            for klass, count in count_per_type.items():
                objcount[klass][index] = count

                highcount = max(count, sample_highcount.get(klass, 0))
                sample_highcount[klass] = highcount

        # get the topn classes with the highest object count, the idea to show
        # spikes
        topn_classes = sorted(
            ((count, klass) for klass, count in sample_highcount.items()), reverse=True
        )[:topn]

        # this creates the valley in the graph, we assume that there is a
        # startup interval between sampling files and that the end of the last
        # sample should not continue directly by the next sample, so we need to
        # force the value to zero
        for __, klass in topn_classes:
            if klass in alltime_data:
                points = alltime_data[klass]
            else:
                points = alltime_factory()

            start = position + 1
            end = position + len(data) + 1
            points[start:end] = objcount[klass]
            alltime_data[klass] = points

        sample_timestamps = [sample[TIMESTAMP] for sample in data]
        sample_timestamps.append(sample_timestamps[-1] + ONESECOND_TIMEDELTA)
        sample_timestamps.insert(0, sample_timestamps[0] - ONESECOND_TIMEDELTA)
        alltime_timestamps.extend(sample_timestamps)

        position += len(data) + 2

    fig, axes = plt.subplots()

    # we don't need a point before the first sample and after the last
    labels = alltime_data.keys()
    values = [alltime_data[label] for label in labels]

    if not values:
        print("file is empty")
        return

    # plot only once to share the labels and colors
    axes.stackplot(alltime_timestamps, *values, labels=labels)
    axes.legend(loc="upper left", fontsize="small")

    plot_date_axis(axes)
    plot_configure(fig)
    plt.savefig(output)


def memory_timeline(output, data_list):
    """Plots all the data in data_list into a single axis, pinning the y-axis
    minimum at zero.

    This plot was created to compare multiple executions of the application,
    removing skew in both axes.
    """
    import matplotlib.pyplot as plt

    data_list = sorted(data_list, key=lambda list_: list_[0][TIMESTAMP])

    fig, memory_axes = plt.subplots()

    last_ts: Optional[Any] = None
    memory_max = 0.0

    for data in data_list:
        timestamp = [line[TIMESTAMP] for line in data]
        memory = [line[MEMORY] for line in data]

        memory_max = max(max(memory), memory_max)

        memory_axes.plot(timestamp, memory, color="b")

        if last_ts is not None:
            plt.axvspan(last_ts, timestamp[0], color="y", alpha=0.1, lw=0)

        last_ts = timestamp[-1]

    memory_max *= 1.1

    memory_axes.set_ylim(0, memory_max)

    plot_date_axis(memory_axes)
    memory_axes.set_ylabel("Memory (MB)", color="b")
    plot_configure(fig)
    plt.savefig(output)


def memory_subplot(output, data_list):
    """Plots all data in separated axes, a simple way to look at distinct
    executions, keep in mind that the time-axis will be skewed, since each plot
    has a differente running time but the same plotting area."""
    import matplotlib.pyplot as plt
    from matplotlib import dates

    number_plots = len(data_list)
    fig, all_memory_axes = plt.subplots(1, number_plots, sharey="row")

    if number_plots == 1:
        all_memory_axes = [all_memory_axes]

    memory_max = 0.0
    for line in chain(*data_list):
        memory_max = max(memory_max, line[MEMORY])

    # give room for the lines and axes
    memory_max *= 1.1

    hour_fmt = dates.DateFormatter("%H:%M")
    for count, (data, memory_axes) in enumerate(zip(data_list, all_memory_axes)):
        timestamp = [line[TIMESTAMP] for line in data]
        memory = [line[MEMORY] for line in data]

        dt_start_time = timestamp[0]
        hours = timestamp[-1] - dt_start_time
        label = "{start_date:%Y-%m-%d}\n{runtime}".format(start_date=dt_start_time, runtime=hours)

        memory_axes.plot(timestamp, memory, color="b")
        memory_axes.set_ylim(0, memory_max)
        memory_axes.xaxis.set_major_formatter(hour_fmt)
        memory_axes.set_xlabel(label)

        if len(data_list) == 1 or count == 0:
            memory_axes.set_ylabel("Memory (MB)")
        else:
            memory_axes.get_yaxis().set_visible(False)

    fig.autofmt_xdate()
    plot_configure(fig)
    plt.savefig(output)


def latency_scatter(output, data_list):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots()

    data_list = sorted(data_list, key=lambda list_: list_[0])

    timestamp, latency = [], []
    for timestamps in data_list:
        last = timestamps.pop(0)
        for current in timestamps:
            timedelta = current - last
            # seconds = timedelta.total_seconds() - interval
            seconds = timedelta.total_seconds()
            timestamp.append(current)
            latency.append(seconds)
            last = current

    if latency:
        axes.set_ylabel("Latency (sec)")
        axes.scatter(timestamp, latency, s=10, alpha=0.1, marker=",", edgecolors="none")
        axes.set_xlim(min(timestamp), max(timestamp))
        axes.set_ylim(0, max(latency) * 1.1)

    last_ts: Optional[Any] = None
    for timestamps in data_list:
        if not timestamps:
            continue

        if last_ts is not None:
            plt.axvspan(last_ts, timestamps[0], color="y", alpha=0.1, lw=0)

        last_ts = timestamps[-1]

    plot_date_axis(axes)
    plot_configure(fig)
    plt.savefig(output)


def objcount_data(filepath):
    # the file dosn't contain just one pickled object, but a sequence of
    # pickled dictionaries (look at the sample_objects for details)
    #
    # note: this only works with objects that keep track of the reading
    # position

    data = []
    try:
        with open(filepath, "rb") as handler:
            while True:  # while we dont hit EOFError
                timestamp_string, object_count = pickle.load(handler)
                timestamp = ts_to_dt(timestamp_string)
                line = (timestamp, object_count)

                if line:
                    data.append(line)
    except EOFError:
        # we loaded all the objects from the file
        pass

    return data


def memory_data(filepath):
    def convert_line(line):
        """returns a tuple (timestamp, memory_usage)"""
        return (ts_to_dt(line[TIMESTAMP]), float(line[MEMORY]))

    with open(filepath) as handler:
        # the format of the file has two columns:
        # timestamp memory_mb
        data = [line.split() for line in handler if line]

    return list(map(convert_line, data))


def latency_data(filepath):
    with open(filepath) as handler:
        return [ts_to_dt(line.split()[0]) for line in handler if line]


def main():
    import argparse

    parser = argparse.ArgumentParser()

    # first action
    action_parser = parser.add_subparsers(dest="action")
    memory_parser = action_parser.add_parser("memory")
    latency_parser = action_parser.add_parser("latency")

    # memory subaction
    memory_plot_parser = memory_parser.add_subparsers(dest="plot")
    memory_subplot_parser = memory_plot_parser.add_parser("subplot")
    memory_timeline_parser = memory_plot_parser.add_parser("timeline")
    memory_objcount_parser = memory_plot_parser.add_parser("objcount")

    memory_subplot_parser.add_argument("data", nargs="+")
    memory_subplot_parser.add_argument("--output", default="memory.png", type=str)

    memory_timeline_parser.add_argument("data", nargs="+")
    memory_timeline_parser.add_argument("--output", default="memory_timeline.png", type=str)

    memory_objcount_parser.add_argument("data", nargs="+")
    memory_objcount_parser.add_argument("--output", default="memory_objcount.png", type=str)
    memory_objcount_parser.add_argument("--topn", default=10, type=int)

    # latency subaction
    latency_plot_parser = latency_parser.add_subparsers(dest="plot")
    latency_scatter_parser = latency_plot_parser.add_parser("scatter")

    latency_scatter_parser.add_argument("data", nargs="+")
    latency_scatter_parser.add_argument("--interval", default=INTERVAL_SECONDS, type=float)
    latency_scatter_parser.add_argument("--output", default="latency_scatter.png", type=str)

    arguments = parser.parse_args()

    # consistent styling
    import matplotlib.pyplot as plt

    plt.style.use("ggplot")

    if arguments.action == "memory" and arguments.plot == "subplot":
        data_list = [memory_data(path) for path in arguments.data]
        data_list = list(filter(len, data_list))
        memory_subplot(arguments.output, data_list)

    elif arguments.action == "memory" and arguments.plot == "timeline":
        data_list = [memory_data(path) for path in arguments.data]
        data_list = list(filter(len, data_list))
        memory_timeline(arguments.output, data_list)

    elif arguments.action == "memory" and arguments.plot == "objcount":
        data_list = [objcount_data(path) for path in arguments.data]
        data_list = list(filter(len, data_list))
        memory_objcount(arguments.output, data_list, topn=arguments.topn)

    elif arguments.action == "latency" and arguments.plot == "scatter":
        data_list = [latency_data(path) for path in arguments.data]
        data_list = list(filter(len, data_list))
        latency_scatter(arguments.output, data_list)


if __name__ == "__main__":
    main()
