"""
Utilities for computing credible regions from SCAT posterior samples.
"""

import logging
from pathlib import Path

import numpy as np
from scipy.stats import chi2

logger = logging.getLogger(__name__)


def compute_credible_region_polygon(
    samples: np.ndarray, confidence: float = 0.9, n_points: int = 100
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute the 2D credible region (as a polygon) from SCAT posterior samples.

    Args:
        samples: (N, 2) array of [latitude, longitude] posterior samples
        confidence: Confidence level for the credible region (default 0.9)
        n_points: Number of points to use for the polygon boundary (default 100)

    Returns:
        Tuple of (latitudes, longitudes) representing the polygon boundary

    Raises:
        ValueError: If samples array is invalid or confidence is out of range
    """
    if samples.shape[1] != 2:
        raise ValueError(f"Expected 2D samples, got shape {samples.shape}")

    if not 0 < confidence < 1:
        raise ValueError(f"Confidence must be between 0 and 1, got {confidence}")

    if len(samples) < 3:
        raise ValueError(f"Need at least 3 samples, got {len(samples)}")

    # Compute mean and covariance
    mean = samples.mean(axis=0)
    cov = np.cov(samples.T)

    # Handle degenerate cases (e.g., all samples at same point)
    if np.linalg.det(cov) < 1e-10:
        logger.warning(
            "Covariance matrix is nearly singular, using small isotropic region"
        )
        # Create a small circular region around the mean
        radius = 0.01  # degrees
        theta = np.linspace(0, 2 * np.pi, n_points)
        latitudes = mean[0] + radius * np.cos(theta)
        longitudes = mean[1] + radius * np.sin(theta)
        return latitudes, longitudes

    # Chi-squared quantile for 2D Gaussian
    q = chi2.ppf(confidence, df=2)

    # Eigen decomposition for shape and orientation
    vals, vecs = np.linalg.eigh(cov)

    # Ensure eigenvalues are positive
    vals = np.maximum(vals, 1e-10)

    # Compute ellipse dimensions
    width, height = 2 * np.sqrt(vals * q)

    # Parametrize ellipse boundary
    theta = np.linspace(0, 2 * np.pi, n_points)
    ellipse = np.column_stack([width / 2 * np.cos(theta), height / 2 * np.sin(theta)])

    # Rotate and translate to mean
    rotated = ellipse @ vecs.T
    polygon = rotated + mean

    latitudes = polygon[:, 0]
    longitudes = polygon[:, 1]

    return latitudes, longitudes


def read_scat_samples(file_path: Path) -> np.ndarray:
    """
    Read SCAT posterior samples from the LegadoSP output file.
    Returns (N, 2) array of [latitude, longitude] samples.
    Note: The last line contains acceptance rate and should be ignored.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"SCAT output file not found: {file_path}")

    samples = []
    with open(file_path) as f:
        lines = f.readlines()

    # Skip the last line which contains acceptance rate
    for line_num, line in enumerate(lines[:-1], 1):
        line = line.strip()
        if not line:
            continue
        values = line.split()
        if len(values) >= 2:  # Need at least lat and lng
            try:
                lat, lng = float(values[0]), float(values[1])
                samples.append([lat, lng])
            except ValueError:
                # skip lines that can't be parsed as floats (e.g., headers)
                continue

    if not samples:
        raise ValueError("No valid samples found in file")
    samples_array = np.array(samples)
    logger.info(f"Loaded {len(samples_array)} posterior samples from {file_path}")
    return samples_array


def compute_credible_region_from_file(file_path: Path, confidence: float = 0.9) -> dict:
    """
    Compute credible region polygon from a SCAT output file.

    Args:
        file_path: Path to the SCAT output file
        confidence: Confidence level for the credible region (default 0.9)

    Returns:
        Dictionary containing:
        - 'polygon': List of [lat, lng] coordinates for the polygon
        - 'center': [lat, lng] of the mean location
        - 'confidence': The confidence level used
        - 'n_samples': Number of posterior samples used
    """
    # Read samples from file
    samples = read_scat_samples(file_path)

    # Compute credible region
    lats, lngs = compute_credible_region_polygon(samples, confidence)

    # Convert to list of [lat, lng] pairs for JSON serialization
    polygon = [[float(lat), float(lng)] for lat, lng in zip(lats, lngs)]

    # Compute center (mean)
    center = [float(samples.mean(axis=0)[0]), float(samples.mean(axis=0)[1])]

    return {
        "polygon": polygon,
        "center": center,
        "confidence": confidence,
        "n_samples": len(samples),
    }
