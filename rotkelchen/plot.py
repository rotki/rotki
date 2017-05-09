import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


def show(stats):
    times = []
    data = []
    for entry in stats:
        times.append(datetime.utcfromtimestamp(entry['date']))
        data.append(entry['data']['net_usd'])

    x = np.array(times)
    y = np.array(data)
    plt.plot(x, y)
    plt.show()
