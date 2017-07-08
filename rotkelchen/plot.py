import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


def show(stats):
    times = []
    data = []
    for entry in stats:
        times.append(datetime.utcfromtimestamp(float(entry['date'])))
        data.append(float(entry['data']['net_usd']))

    x = np.array(times)
    y = np.array(data)
    plt.plot(x, y)
    plt.show()
