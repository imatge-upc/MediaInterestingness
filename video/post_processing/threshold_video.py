"""
Author: Lluc Cardoner

Script for calculating the threshold of the predictions.
Formatting for MAP calculation with Mediaeval script.

"""
from __future__ import print_function

import h5py
import numpy as np
from matplotlib import pyplot as plt

model_num = 65
predictions = '/home/lluc/PycharmProjects/TFG/video/src/LSTM_{}_predictions.h5'.format(model_num)
pred_file = h5py.File(predictions, 'a')


def savitzky_golay(y, window_size, order, deriv=0, rate=1):
    r"""Smooth (and optionally differentiate) data with a Savitzky-Golay filter.
    The Savitzky-Golay filter removes high frequency noise from data.
    It has the advantage of preserving the original shape and
    features of the signal better than other types of filtering
    approaches, such as moving averages techniques.
    Parameters
    ----------
    y : array_like, shape (N,)
        the values of the time history of the signal.
    window_size : int
        the length of the window. Must be an odd integer number.
    order : int
        the order of the polynomial used in the filtering.
        Must be less then `window_size` - 1.
    deriv: int
        the order of the derivative to compute (default = 0 means only smoothing)
    Returns
    -------
    ys : ndarray, shape (N)
        the smoothed signal (or it's n-th derivative).
    Notes
    -----
    The Savitzky-Golay is a type of low-pass filter, particularly
    suited for smoothing noisy data. The main idea behind this
    approach is to make for each point a least-square fit with a
    polynomial of high order over a odd-sized window centered at
    the point.
    Examples
    --------
    t = np.linspace(-4, 4, 500)
    y = np.exp( -t**2 ) + np.random.normal(0, 0.05, t.shape)
    ysg = savitzky_golay(y, window_size=31, order=4)
    import matplotlib.pyplot as plt
    plt.plot(t, y, label='Noisy signal')
    plt.plot(t, np.exp(-t**2), 'k', lw=1.5, label='Original signal')
    plt.plot(t, ysg, 'r', label='Filtered signal')
    plt.legend()
    plt.show()
    References
    ----------
    .. [1] A. Savitzky, M. J. E. Golay, Smoothing and Differentiation of
       Data by Simplified Least Squares Procedures. Analytical
       Chemistry, 1964, 36 (8), pp 1627-1639.
    .. [2] Numerical Recipes 3rd Edition: The Art of Scientific Computing
       W.H. Press, S.A. Teukolsky, W.T. Vetterling, B.P. Flannery
       Cambridge University Press ISBN-13: 9780521880688
    """
    import numpy as np
    from math import factorial

    try:
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order + 1)
    half_window = (window_size - 1) // 2
    # precompute coefficients
    b = np.mat([[k ** i for i in order_range] for k in range(-half_window, half_window + 1)])
    m = np.linalg.pinv(b).A[deriv] * rate ** deriv * factorial(deriv)
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - np.abs(y[1:half_window + 1][::-1] - y[0])
    lastvals = y[-1] + np.abs(y[-half_window - 1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve(m[::-1], y, mode='valid')


def running_mean(l, N):
    s = 0
    result = list(0 for x in l)

    for i in range(0, N):
        s = s + l[i]
        result[i] = s / (i + 1)

    for i in range(N, len(l)):
        s = s - l[i - N] + l[i]
        result[i] = s / N

    return result


def calculate_threshold(video_num, second_derivative_threshold=0.01, smooth=True, save=True, plot=False):
    """Calculates the threshold value for all the predicted labels for the segments of one video"""
    pred = []
    video_group = pred_file['back_label_mapping']['video_{}'.format(video_num)]
    for seg in video_group:
        pred.append(video_group[seg][()])
    pred = np.array(pred)  # array with all the predicted labels of the segments of one video
    pred = np.sort(pred)  # sort the array from lower to higher
    pred_norm = pred / pred.max(axis=0)  # normalize between 0 and 1
    # curve = savitzky_golay(pred, window_size=21, order=3)  # smooth the curve
    curve = running_mean(pred_norm, 5)  # smooth the curve

    # no smoothed curve
    first_derivative = np.gradient(pred_norm)
    second_derivative = np.gradient(first_derivative)

    # smoothed curve
    first_derivative_c = np.gradient(curve)
    second_derivative_c = np.gradient(first_derivative_c)

    der = second_derivative if not smooth else second_derivative_c
    for x, e in enumerate(der):
        if e > second_derivative_threshold:
            break
    print(x, pred[x])  # get the prediction at the x position

    if plot:
        plt.figure(1)
        plt.subplot(221)
        plt.plot(pred_norm)
        plt.subplot(223)
        plt.plot(curve)
        plt.subplot(222)
        plt.plot(range(second_derivative.size), second_derivative, c='r')
        t = [second_derivative_threshold] * len(second_derivative)
        plt.plot(range(len(t)), t)
        plt.subplot(224)
        plt.plot(range(second_derivative_c.size), second_derivative_c, c='r')
        z = [second_derivative_threshold] * len(second_derivative_c)
        plt.plot(range(len(z)), z)
        plt.show()

    if save:
        dir = 'threshold_{}'.format(second_derivative_threshold)
        if '/{}'.format(dir) not in pred_file:
            thr = pred_file.create_group(dir)
        else:
            thr = pred_file[dir]
        thr.create_dataset('video_{}'.format(video_num), data=pred[x])

    return pred[x]


def calculate_threshold_all_data(second_derivative_threshold=0.0, plot=False):
    pred = []
    labels = pred_file['back_label_mapping']
    for v in labels:
        # print(v)
        for seg in labels[v]:
            # print(seg)
            pred.append(labels[v][seg][()])

    pred = np.array(pred)  # array with all the predicted labels of the segments of one video
    pred = np.sort(pred)  # sort the array from lower to higher
    pred_norm = pred / pred.max(axis=0)  # normalize between 0 and 1
    curve = running_mean(pred_norm, 5)  # smooth the curve

    coefficients = np.polyfit(np.array(range(pred_norm.size)), pred_norm, deg=3)

    f = lambda p: coefficients[0] * p ** 3 + coefficients[1] * p ** 2 + coefficients[2] * p + coefficients[3]
    poly = np.fromfunction(f, shape=pred_norm.shape)  # fitted curve as a order 3 polynomial
    # poly = poly / poly.max(axis=0)
    # no smoothed curve
    first_derivative = np.gradient(pred_norm)
    second_derivative = np.gradient(first_derivative)

    # smoothed curve
    first_derivative_c = np.gradient(curve)
    second_derivative_c = np.gradient(first_derivative_c)

    # fitted curve
    first_derivative_p = np.gradient(poly)
    # first_derivative_p = first_derivative_p / first_derivative_p.max(axis=0)
    second_derivative_p = np.gradient(first_derivative_p)
    # second_derivative_p = second_derivative_p / second_derivative_p.max(axis=0)

    # der = second_derivative if not smooth else second_derivative_c

    # get the threshold
    for x, e in enumerate(second_derivative_p):
        if e > second_derivative_threshold:
            break

    # min_value = first_derivative_p.min(axis=0)
    # x = np.where(first_derivative_p == min_value)[0][0]
    print(x, pred[x])  # get the prediction at the x position

    if plot:
        plt.figure(1)
        plt.subplot(221)
        plt.plot(pred_norm)
        plt.plot(poly)
        # plt.subplot(334)
        # plt.plot(curve)
        plt.subplot(222)
        plt.plot(poly)

        # plt.subplot(332)
        # plt.plot(range(first_derivative.size), first_derivative, c='r')
        # plt.subplot(335)
        # plt.plot(range(first_derivative_c.size), first_derivative_c, c='r')
        plt.subplot(223)
        plt.plot(range(first_derivative_p.size), first_derivative_p, c='r')
        #
        # plt.subplot(333)
        # plt.plot(range(second_derivative.size), second_derivative, c='r')
        # t = [second_derivative_threshold] * len(second_derivative)
        # plt.plot(range(len(t)), t)
        # plt.subplot(336)
        # plt.plot(range(second_derivative_c.size), second_derivative_c, c='r')
        # z = [second_derivative_threshold] * len(second_derivative_c)
        # plt.plot(range(len(z)), z)
        plt.subplot(224)
        plt.plot(range(second_derivative_p.size), second_derivative_p, c='r')
        # h = [second_derivative_threshold] * len(second_derivative_p)
        # plt.plot(range(len(h)), h)

        plt.show()

    return pred[x]


def create_submit_results(video_num, th, sdt):
    """Create the submit result file"""
    output = '/home/lluc/PycharmProjects/TFG/trec_eval.8.1/LSTM_results/me16in_wien_video_LSTM{}-{}.txt'.format(
        model_num, sdt)
    out_file = open(output, 'a')
    video_group = pred_file['back_label_mapping']['video_{}'.format(video_num)]
    for i in range(len(video_group.keys())):  # to make sure it is in order
        for seg in video_group:
            name = seg.split('_')
            if int(name[0]) == i:
                prob = video_group[seg][()]
                classification = 0 if prob < th else 1  # classification
                out_file.write('video_{},{},{},{}\n'.format(video_num, name[1], classification, prob))


def create_all_submit_results(th, sdt):
    """Create the submit result file"""
    output = '/home/lluc/PycharmProjects/TFG/trec_eval.8.1/LSTM_results/me16in_wien_video_LSTM{}-{}-{}.txt'.format(
        model_num, sdt, th)
    out_file = open(output, 'a')
    data = pred_file['back_label_mapping']
    for v in data:
        video_group = data[v]
        for i in range(len(video_group.keys())):  # to make sure it is in order
            for seg in video_group:
                name = seg.split('_')
                if int(name[0]) == i:
                    prob = video_group[seg][()]
                    classification = 0 if prob < th else 1  # classification
                    out_file.write('{},{},{},{}\n'.format(v, name[1], classification, prob))


# calculate_threshold(52, second_derivative_threshold=0.01, save=False, plot=True)

# calculate threshold for al videos
sdth = 0.0
threshold = calculate_threshold_all_data(second_derivative_threshold=sdth, plot=True)
# create_all_submit_results(th=threshold, sdt=sdth)


# calculate different threshold for each video
# for v in range(52, 52 + 26):
#     sdth = 0.0
#     threshold = calculate_threshold(v, second_derivative_threshold=sdth, smooth=True, save=False, plot=False)
#     print(v, threshold)
#     create_submit_results(v, th=threshold, sdt=sdth)
