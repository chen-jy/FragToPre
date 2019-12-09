import argparse

import pyopenms as ms
import numpy as np

def peak_pick(exp, min_req=1, window_size=float('Inf'), small_peak=0.1, strict=True,
              sequential=True):
    """A custom peak picker for use with im_binning, since PeakPickerHiRes always
    destroys the data. The idea is to get rid of satellite peaks so that matching
    features within a bin is not required, and erroneous features are minimized.

    Algorithm:
    1. Sort peaks by increasing m/z.
    2. Create a boolean array with a False for every peak.
    3. Walk from left to right and find a local maximum.
    4. For each local maximum, go left and right (within a window) until the current peak
        is less than x% of the local maximum.
    5. Mark all of the peaks in the peak set as True.
    6. Create a new peak with intensity being the sum of the intensities of the peaks in
        the peak set and m/z being an intensity-weighted average.

    Alternate algorithm (for sequential=False):
    1. Sort peaks by increasing m/z.
    2. Create a lookup table, storing each peak's intensity and index in the m/z-sorted
        spectrum.
    3. Sort the lookup table by the peaks' intensities, descending.
    4. Continue with the normal algorithm, but instead of iterating through peaks in the
        order of the m/z-sorted spectrum, go in the order of the intensity-sorted lookup
        table.

    Args:
        exp (MSExperiment): The OpenMS experiment to be peak picked.
        min_req (int): The required number of decreasing/non-increasing peaks to either
            side of a peak in order to be considered a local maximum.
        window_size (float): The maximum m/z distance left/right from the initial peak to
            consider.
        small_peak (float): The multiplier to use when deciding if a peak is x% smaller
            than the initial peak.
        strict (bool): If true, peaks must be non-increasing from the initial peak.
            Otherwise, a single peak is allowed to break this rule.
        sequential (bool): If true, run the algorithm normally. Otherwise, use the
            alternate algorithm.

    Returns:
        MSExperiment: An OpenMS experiment corresponding to the input, but peak-picked.
    """
    exp.sortSpectra()
    spectra = exp.getSpectra()
    new_exp = ms.MSExperiment()

    for spec in spectra:
        if spec.getMSLevel() != 1:
            continue
        print("Peak picking RT", spec.getRT())
        
        num_peaks = spec.size()
        spec.sortByPosition()
        peak_idx = []

        if not sequential:
            # Create the lookup table
            for i in range(num_peaks):
                peak_idx.append([spec[i].getIntensity(), i])

            peak_idx = sorted(peak_idx, reverse=True)

        new_spec = ms.MSSpectrum()
        new_spec.setMSLevel(1)
        new_spec.setRT(spec.getRT())

        picked = [False] * num_peaks

        # Begin peak picking
        for idx in range(num_peaks):
            i = idx if sequential else peak_idx[idx][1]
            if picked[i]:
                continue

            init_intensity = spec[i].getIntensity()
            total_intensity = spec[i].getIntensity()
            init_position = spec[i].getPos()
            left_picked, right_picked = 0, 0
            low_bound, high_bound = i, i

            # Flag for a single increase in intensity (when strict=False)
            sflag = False
            threshold = min_req
            
            # Walk left
            for j in range(i - 1, -1, -1):
                # TODO: test this
                if picked[j]:
                    break

                if abs(spec[j].getPos() - init_position) > window_size:
                    break

                if spec[j].getIntensity() > spec[j + 1].getIntensity():
                    # Should not start with immediate "abnormal" peaks (3rd condition)
                    if strict or sflag or j + 1 == i:
                        break
                    sflag = True
                    # Need to end the series with a lower peak, so "increase min_req"
                    threshold += 1

                total_intensity += spec[j].getIntensity()
                left_picked += 1
                low_bound -= 1

                if left_picked >= threshold and \
                    spec[j].getIntensity() <= init_intensity * small_peak:
                    break

            if left_picked < threshold:
                continue

            sflag = False
            threshold = min_req

            # Walk right
            for j in range(i + 1, num_peaks):
                # TODO: test this
                if picked[j]:
                    break

                if abs(spec[j].getPos() - init_position) > window_size:
                    break

                if spec[j].getIntensity() > spec[j - 1].getIntensity():
                    if strict or sflag or j - 1 == i:
                        break
                    sflag = True
                    threshold += 1

                total_intensity += spec[j].getIntensity()
                right_picked += 1
                high_bound += 1

                if right_picked >= threshold and \
                    spec[j].getIntensity() <= init_intensity * small_peak:
                    break

            if right_picked < threshold:
                continue

            total_position = 0
            for j in range(low_bound, high_bound + 1):
                picked[j] = True
                # Calculate the intensity-weighted m/z position
                total_position += spec[j].getPos() * (spec[j].getIntensity() /
                                                      total_intensity)

            p = ms.Peak1D()
            p.setIntensity(total_intensity)
            p.setPos(total_position)
            new_spec.push_back(p)

        new_exp.addSpectrum(new_spec)

    return new_exp

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Custom peak picker.')
    parser.add_argument('--input', action='store', required=True, type=str)
    parser.add_argument('--output', action='store', required=True, type=str)

    args = parser.parse_args()

    exp = ms.MSExperiment()
    print('Loading mzML input file....................', end='', flush=True)
    ms.MzMLFile().load(args.input, exp)
    print('Done')

    new_exp = peak_pick(exp)
    ms.MzMLFile().store(args.output, new_exp)
