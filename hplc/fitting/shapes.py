"""Area-normalized positive chromatographic component shapes."""
import numpy as np
from scipy.stats import exponnorm


def component(x, parameters, model):
    area, center, sigma = parameters[:3]
    if model == "gaussian":
        return area * np.exp(-0.5 * ((x - center) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))
    return area * exponnorm.pdf(x, parameters[3] / sigma, loc=center, scale=sigma)


def components(x, parameters, model):
    return np.asarray([component(x, p, model) for p in parameters])
