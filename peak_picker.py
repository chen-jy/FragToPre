import argparse

import pyopenms as ms
import numpy as np

def peak_pick(exp, maxima_threshold=3):
    """A custom peak picker for use with im_binning, since PeakPickerHiRes always
    destroys the data. The idea is to get rid of satellite peaks so that matching
    features within a bin is not required.

    1. Peaks are sorted.
    2. A boolean array is created with a False for every existing peak.
    3. Iterate forward and find a peak with the local highest intensity.
        - Need to check further forward (more than just the next peak)
    4. Go left and right (within a window) until the current peak is less than 5-10% of
        the most intense local peak.
    5. Mark all of the peaks as True.
    6. Create a new peak with its intensity being the sum of the intensities of the newly
        marked peaks and its m/z being a weighted average.

    Args:
        exp (MSExperiment): The OpenMS experiment to be peak picked.
        maxima_threshold (int): The required number of decreasing/non-increasing peaks to
            either side of a peak in order to be considered a local maximum.

    Returns:
        MSExperiment: An OpenMS experiment corresponding to the input, but peak-picked.
    """
    exp.sortSpectra()
    spectra = exp.getSpectra()
    new_exp = ms.MSExperiment()

    for spec in spectra:
        if spec.getMSLevel() != 1:
            continue

        spec.sortByPosition()
        num_peaks = spec.size()
        new_spec = ms.MSSpectrum()

        picked = [False] * num_peaks

        for i in range(0, num_peaks):
            if picked[i] == True:
                continue

            init_intensity = spec[i].getIntensity()
            total_intensity = spec[i].getIntensity()
            total_position = spec[i].getPos()
            left_picked, right_picked, 0, 0
            low_bound, high_bound = i, i
            
            # Maybe have the option to allow for a single increase in intensity?
            for j in range(i - 1, -1, -1):
                if spec[j].getIntensity() > spec[j + 1].getIntensity():
                    if left_picked < maxima_threshold:
                        left_picked = -1
                    break
                else:
                    total_intensity += spec[j].getIntensity()
                    total_position += spec[j].getPos()
                    left_picked += 1
                    low_bound -= 1

                    if left_picked >= maxima_threshold and \
                        spec[j].getIntensity <= init_intensity * 0.10:
                        break

            if left_picked == -1:
                continue

            for j in range(i + 1, num_peaks):
                if spec[j].getIntensity() > spec[j - 1].getIntensity():
                    if right_picked < maxima_threshold:
                        right_picked = -1
                    break
                else:
                    total_intensity += spec[j].getIntensity()
                    total_position += spec[j].getPos()
                    right_picked += 1
                    high_bound += 1

                    if right_picked >= maxima_threshold and \
                        spec[j].getIntensity <= init_intensity * 0.10:
                        break

            if right_picked == -1:
                continue

            for j in range(low_bound, high_bound + 1):
                picked[j] = True

            p = ms.Peak1D()
            p.setIntensity(total_intensity)
            p.setPos(total_position / (left_picked + right_picked + 1))
            new_spec.push_back(p)

        new_exp.addSpectrum(new_spec)

    return new_exp

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Custom peak picker.')
    parser.add_argument('--in', action='store', required=True, type=str)
    parser.add_argument('--out', action='store', required=True, type=str)

    args = parser.parse_args()

    exp = ms.MSExperiment()
    print('Loading mzML input file....................', end='', flush=True)
    ms.MzMLFile().load(args.infile + '.mzML', exp)
    print('Done')

    new_exp = peak_pick(exp)