import datetime
import os

import gevent_profiler
import GreenletProfiler


class CpuProfiler:
    def __init__(self, datadir: str) -> None:
        date_now = datetime.datetime.now(tz=datetime.timezone.utc)
        # create a new file every time instead of overwritting the latest profiling
        summary_file = f'{date_now:%Y%m%d_%H%M}_profile_summary'
        stats_file = f'{date_now:%Y%m%d_%H%M}_profile_stats'

        summary_path = os.path.join(datadir, summary_file)
        stats_path = os.path.join(datadir, stats_file)

        gevent_profiler.set_trace_output(None)
        gevent_profiler.set_summary_output(summary_path)
        gevent_profiler.set_stats_output(stats_path)

        GreenletProfiler.set_clock_type('cpu')
        GreenletProfiler.start()

        self.datadir = datadir

    def stop(self) -> None:
        GreenletProfiler.stop()
        date_now = datetime.datetime.now(tz=datetime.timezone.utc)
        greenlet_file = f'{date_now:%Y%m%d_%H%M}_profile_greenlet.callgrind'
        greenlet_path = os.path.join(self.datadir, greenlet_file)

        stats = GreenletProfiler.get_func_stats()
        stats.print_all()
        stats.save(greenlet_path, type='callgrind')
