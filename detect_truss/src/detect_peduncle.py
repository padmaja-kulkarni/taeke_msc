# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 18:16:42 2020

@author: taeke
"""

import os
from detect_truss.util import make_dirs, load_rgb
from detect_truss.util import change_brightness, plot_timer

from detect_truss.ProcessImage import ProcessImage
from detect_truss.detect_peduncle_2 import detect_peduncle # visualize_skeleton, get_node_coord, threshold_branch_length, skeletonize_img

from detect_truss.timer import Timer
from detect_truss.counter import Counter

def main():

    # %% init
    nDigits = 3
    i_start = 1
    i_end = 25
    N = i_end - i_start

    save = True

    drive = "UBUNTU 16_0" # "backup"
    pwd_current = os.path.join(os.sep, "media", "taeke", drive, "thesis_data",
                               "detect_truss")
    dataset = 'real_blue' #  'depth_blue'  # "drawing" #  "empty" # "artificial" # 'failures'#

    pwd_data = os.path.join(pwd_current, "data", dataset)
    pwd_results = os.path.join(pwd_current, "results", dataset, "06_peduncle")

    make_dirs(pwd_results)

    brightness = 0.85

    for count, i_tomato in enumerate(range(i_start, i_end)):  # 10, 11
        print("Analyzing image %d out of %d" % (i_tomato, N))

        tomato_name = str(i_tomato).zfill(nDigits)
        file_name = tomato_name + ".png"

        img_rgb = load_rgb(pwd_data, file_name, horizontal=True)

        image = ProcessImage(use_truss=True,
                             name=tomato_name,
                             pwd=pwd_results,
                             save=False)

        image.add_image(img_rgb)

        image.color_space()
        image.segment_image()
        image.filter_image()
        image.rotate_cut_img()
        image.detect_tomatoes()

        segment_img = image.get_segmented_image(local=True)
        peduncle_img = image.get_peduncle_image(local=True)
        segment_img_bright = change_brightness(segment_img, brightness)

        skeleton_img, branch_data, coord_junc, coord_end = detect_peduncle(peduncle_img,
                                                                           bg_img=segment_img_bright,
                                                                           save=True,
                                                                           name=tomato_name,
                                                                           pwd=pwd_results)

    # name_space = 'peduncle'
    # plot_timer(Timer.timers[name_space].copy(), N=N, threshold=0.1, pwd=pwd_results, title='time')
    # print(Counter.counters[name_space].copy())


if __name__ == '__main__':
    main()
