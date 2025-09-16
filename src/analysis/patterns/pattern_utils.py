import numpy as np
from typing import List

def cluster_levels(levels: List[float], tolerance: float = 0.5) -> List[float]:
    """
    Groups close price levels together into clusters and returns the mean of each cluster.

    Args:
        levels (List[float]): A list of price levels to cluster.
        tolerance (float): The percentage difference allowed to form a cluster.

    Returns:
        List[float]: A list containing the mean value of each identified cluster.
    """
    if not levels:
        return []

    levels.sort()

    clusters = []
    if not levels:
        return clusters

    current_cluster = [levels[0]]

    for i in range(1, len(levels)):
        # Compare with the last item in the current cluster
        if (levels[i] - current_cluster[-1]) / current_cluster[-1] * 100 <= tolerance:
            current_cluster.append(levels[i])
        else:
            clusters.append(np.mean(current_cluster))
            current_cluster = [levels[i]]

    if current_cluster:
        clusters.append(np.mean(current_cluster))

    return clusters
