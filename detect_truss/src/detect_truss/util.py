#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 14 21:21:28 2020

@author: taeke
"""

import os
import cv2
import numpy as np
import warnings
import copy
from matplotlib import pyplot as plt
from matplotlib.offsetbox import (OffsetImage, AnnotationBbox)

tomato_color = (255,0,0)
peduncle_color = (0, 255, 0)
junction_color = (255, 0, 255)
end_color = (255, 255, 0)
gray_color = (150, 150, 150)

def make_dirs(pwd):
    if not os.path.isdir(pwd):
        print("New path, creating a new folder: " + pwd)
        os.makedirs(pwd)

def load_rgb(pwd, name, horizontal = True):
    
    #load image
    name_full = os.path.join(pwd, name)
    
    if not os.path.exists(name_full):
        print('Cannot load RGB: path does not exist' + name_full)
        return None
        
    img_bgr = cv2.imread(name_full)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    shape = img_rgb.shape[:2]
    
    # transpose image if required
    if horizontal:
        if shape[0] > shape[1] :
            img_rgb = np.transpose(img_rgb, [1,0,2])
            shape = img_rgb.shape[:2]

    if img_rgb is None:
        print("Failed to load image from path: %s" %(name_full))

    return img_rgb

def bin2img(binary, dtype = np.uint8, copy = False):
    'convets an incomming binary image to the desired data type, defualt: uint8'
    max_value = np.iinfo(dtype).max       
    return binary.astype(dtype, copy = copy) * max_value
    
def img2bin(img, copy = False):
    
    dtype = bool
    return img.astype(dtype, copy = copy) 

def remove_blobs(img_in):
    dtype = img_in.dtype
    value = np.iinfo(dtype).max   
    
    # initialize outgoing image
    img_out = np.zeros(img_in.shape[:2], dtype)
    
    # the extra [-2:] is essential to make it work with varios cv2 ersions
    contours, _ = cv2.findContours(img_in, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[-2:]
    
    # only when the image contains a contour
    if len(contours) != 0:
        # print('Filling largest blob...')
        cnt = max(contours, key=cv2.contourArea)
        cv2.drawContours(img_out, [cnt], -1, value, cv2.FILLED)
        # print('Done!...')
    return cv2.bitwise_and(img_in, img_out)

def add_border(imOriginal, location, sizeBorder):

    sizeOriginal = imOriginal.shape
    location = location.astype(int)
    
    imBorder = np.zeros(sizeBorder[0:2], np.uint8)

    colStart = location[0, 0]
    colEnd = location[0, 0] + sizeOriginal[1]
    
    rowStart = location[0, 1]
    rowEnd = location[0, 1] + sizeOriginal[0]
    
    
    
    if (rowEnd > sizeBorder[0]):
        warnings.warn('cutting immage')
        rowEnd = sizeBorder[0]
    
   
    imBorder[rowStart:rowEnd, colStart:colEnd] = imOriginal[0:rowEnd - rowStart, :]
    
    return imBorder
        
def rot2or(loc, dim, alpha):
    # loc in [rows, cols]
    
    N = loc.shape[0]
    LOC = np.empty((N,2))
    
    for i in range(0, N):
        col = loc[i, 0]
        row = loc[i, 1]
        H = dim[0]
        W = dim[1]
        
        if (alpha > np.pi or alpha < -np.pi):
            warnings.warn('Are you using radians?')
        
        # trig equations depend on angle
        if alpha < 0:
            COL = col*np.cos(alpha) - row*np.sin(alpha) + np.cos(alpha)*np.sin(alpha)*H
            ROW = col*np.sin(alpha) + row*np.cos(alpha) + np.sin(alpha)*np.sin(alpha)*H
        else:
            COL = col*np.cos(alpha) - row*np.sin(alpha) + np.sin(alpha)*np.sin(alpha)*W
            ROW = col*np.sin(alpha) + row*np.cos(alpha) - np.cos(alpha)*np.sin(alpha)*W
            
        LOC[i, :] = np.matrix((COL, ROW))
    return LOC

def translation_rot2or(dim, alpha):
    
    H = dim[0]
    W = dim[1]
    
    if (alpha > np.pi or alpha < -np.pi):
        warnings.warn('Are you using radians?')
    
    # trig equations depend on angle
    if alpha < 0:
        col = np.cos(alpha)*np.sin(alpha)*H
        row = np.sin(alpha)*np.sin(alpha)*H
    else:
        col = np.sin(alpha)*np.sin(alpha)*W
        row = np.cos(alpha)*np.sin(alpha)*W
            

    return (col, row)

def or2rot(dim, alpha):

    if (alpha > np.pi or alpha < -np.pi):
         warnings.warn('Are you using radians?')

    H = dim[0]
    W = dim[1]

    if alpha > 0:
        X = 1
        Y = W * np.sin(alpha)
    else:
        X = -H * np.sin(alpha)
        Y = 1
    
    LOC = np.matrix((X, Y))
    return LOC

def label_img(data, centers):
    dist = abs(data - np.transpose(centers))
    labels = np.argmin(dist,1).astype(np.int32)
    return np.expand_dims(labels, axis=1)    


def stack_segments(imRGB, background, tomato, peduncle):
    # stack segments
    
    [h, w] = imRGB.shape[:2]
    
    # set labels
    backgroundLabel = 0
    tomatoLabel = 1
    peduncleLabel = 2
    
    # label pixels
    pixelLabel = np.zeros((h,w), dtype= np.int8)
    pixelLabel[background > 0] = backgroundLabel
    pixelLabel[cv2.bitwise_and(tomato, cv2.bitwise_not(peduncle))>0] = tomatoLabel
    pixelLabel[peduncle > 0] = peduncleLabel
    
    # get class colors
    colorBackground  = np.uint8(np.mean(imRGB[pixelLabel == backgroundLabel], 0))
    colorTomato = np.uint8(np.mean(imRGB[pixelLabel == tomatoLabel], 0))
    colorPeduncle = np.uint8(np.mean(imRGB[pixelLabel == peduncleLabel], 0))
    color = np.vstack([colorBackground, colorTomato, colorPeduncle])
    
    # visualize
    res = color[pixelLabel.flatten()]
    res2 = res.reshape((h,w,3))
    
    return res2

def save_img(img, pwd, name, resolution = 300, title = "", titleSize = 20, ext = 'png'):
        plt.rcParams["savefig.format"] = ext
        plt.rcParams["savefig.bbox"] = 'tight' 
        plt.rcParams['axes.titlesize'] = titleSize
        
    
        fig = plt.figure() 
        plt.imshow(img)
        plt.axis('off')
        if title is not None:
            plt.title(title)
        
        # https://stackoverflow.com/a/27227718
        plt.gca().set_axis_off()
        plt.subplots_adjust(top = 1, bottom = 0, right = 1, left = 0, 
            hspace = 0, wspace = 0)
        plt.margins(0,0)
        plt.gca().xaxis.set_major_locator(plt.NullLocator())
        plt.gca().yaxis.set_major_locator(plt.NullLocator())
        
        # make dir if it does not yet exist        
        make_dirs(pwd)        
        fig.savefig(os.path.join(pwd, name), dpi = resolution, bbox_inches='tight', pad_inches=0)
        
def save_fig(fig, pwd, name, resolution = 300, title = "", titleSize = 20, ext = 'png'):
        
        SMALL_SIZE = 8
        MEDIUM_SIZE = 15
        BIGGER_SIZE = 20
    
        plt.rcParams["savefig.format"] = ext
        plt.rcParams["savefig.bbox"] = 'tight' 
        # plt.rcParams['axes.titlesize'] = titleSize
        
        plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
        plt.rc('xtick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
    
       
        for ax in fig.get_axes():
            ax.label_outer()
        
        
        for ax in fig.get_axes():
            # ax.yaxis.set_major_locator(plt.nulllocator())\
            ax.set_yticklabels([])
        plt.margins(0,0) 
        
        # make dir if it does not yet exist   
        make_dirs(pwd)
        fig.savefig(os.path.join(pwd, name), dpi = resolution, bbox_inches='tight', pad_inches=0)

def add_circles(img_rgb, centers, radii = 5, color = (255,255,255), thickness = 5, 
                pwd = None, name = None, title = ""):

    if isinstance(centers, (list, tuple, np.matrix)):  
        centers = np.array(centers, ndmin=2)   
 
    # if a single radius is give, we repeat the value
    if not isinstance(radii, (list, np.ndarray)):
        radii = [radii] * centers.shape[0]
       
    # if empty we can not add any circles
    if centers.shape[1] == 0:
        return img_rgb

    # centers should be integers       
    centers = np.round(centers).astype(dtype = int) # (col, row)
    radii = np.round(radii).astype(dtype = int) # (col, row)    

        
    for center, radius in zip(centers, radii):
        cv2.circle(img_rgb, tuple(center), radius, color, thickness) # (col, row)

    if pwd is not None:
        save_img(img_rgb, pwd, name, title = "", titleSize = 20, ext = 'png')
            
    return img_rgb

def plot_segments(img_rgb, background, tomato, peduncle, pwd=None, 
                  name=None, title="", alpha = 0.7, thickness = 2):
    
    img_segments = stack_segments(img_rgb, background, tomato, peduncle)
    
    added_image = cv2.addWeighted(img_rgb, 1 - alpha,img_segments,alpha,0)
    added_image = add_contour(added_image, tomato, color = tomato_color, thickness = thickness)
    added_image = add_contour(added_image, peduncle, color = peduncle_color, thickness = thickness)  
    
    if pwd is not None:
        save_img(added_image, pwd, name, title = title)

    return added_image

def plot_features(img_rgb, tomato = None, peduncle = None, grasp = None,
                  alpha = 0.6, thickness = 2, pwd = None, file_name=None, title=""):
    
    img_overlay = np.ones(img_rgb.shape, dtype = np.uint8)
    if tomato:
        img_overlay = add_circles(img_overlay, tomato['centers'], radii = tomato['radii'], color = tomato_color, thickness = -1)
    if peduncle:
        img_overlay = add_circles(img_overlay, peduncle['junctions'], radii = 10, color = junction_color, thickness = -1)    
        # img_overlay = add_circles(img_overlay, peduncle['ends'], radii = 10, color = end_color, thickness = -1)  

    added_image = cv2.addWeighted(img_rgb, 1,img_overlay,alpha,0)

    if tomato:
        added_image = add_circles(added_image, tomato['centers'], 
                                  radii = tomato['radii'], 
                                  color = (0,0,0), #tomato_color, 
                                  thickness = thickness)

        added_image = add_circles(added_image, tomato['com'], radii = 10,
                          color = (255,255,255), 
                          thickness = -1)      
             
        added_image = add_circles(added_image, tomato['com'], radii = 10,
                          color = (0,0,0), 
                          thickness = 3) 
                   
    if peduncle:
        added_image = add_circles(added_image, peduncle['junctions'], radii = 10, color = (0,0,0), thickness = thickness)
        # added_image = add_circles(added_image, peduncle['ends'], radii = 10, color = (0,0,0), thickness = thickness)
    
    if pwd is not None:
        save_img(added_image, pwd, file_name, title = title)

    return added_image
    
def plot_features_result(img_rgb, tomato_pred = None, peduncle = None, grasp = None,
                  alpha = 0.5, thickness = 2, pwd = None, name=None, title=""):
    
    img_overlay = np.ones(img_rgb.shape, dtype = np.uint8)
    if tomato_pred:
        add_circles(img_overlay, tomato_pred['true_pos']['centers'], radii = tomato_pred['true_pos']['radii'], color = tomato_color, thickness = -1)
        add_circles(img_overlay, tomato_pred['false_pos']['centers'], radii = tomato_pred['false_pos']['radii'], color = [150, 0,0], thickness = -1)
    if peduncle:
        img_overlay = add_circles(img_overlay, peduncle['true_pos']['centers'], radii = 10, color = junction_color, thickness = -1)  
        # img_overlay = add_circles(img_overlay, peduncle['false_pos']['centers'], radii = 10, color = junction_color, thickness = -1)  
        # img_overlay = add_circles(img_overlay, peduncle['ends'], radii = 10, color = end_color, thickness = -1)  

    added_image = cv2.addWeighted(img_rgb, 1,img_overlay,alpha,0)

    if tomato_pred:
        added_image = add_circles(added_image, tomato_pred['true_pos']['centers'], 
                                  radii = tomato_pred['true_pos']['radii'], 
                                  color = (0,0,0), 
                                  thickness = thickness)
                                  
        added_image = add_circles(added_image, tomato_pred['false_pos']['centers'], 
                                  radii = tomato_pred['false_pos']['radii'], 
                                  color = (0,0,0),
                                  thickness = thickness)

        added_image = add_circles(added_image, tomato_pred['com'], radii = 10,
                          color = (255,255,255), 
                          thickness = -1)      
             
        added_image = add_circles(added_image, tomato_pred['com'], radii = 10,
                          color = (0,0,0), 
                          thickness = 3) 
                   
    if peduncle:
        added_image = add_circles(added_image, peduncle['true_pos']['centers'], radii = 10, color = (0,0,0), thickness = thickness)
        added_image = add_circles(added_image, peduncle['false_pos']['centers'], radii = 10, color = (255,0,0), thickness = thickness)
        # added_image = add_circles(added_image, peduncle['ends'], radii = 10, color = (0,0,0), thickness = thickness)
    
    if grasp:
        col = grasp['col'] 
        row = grasp['row']
        angle = grasp['angle']
        if (col is not None) and (row is not None) and (angle is not None):
            plot_grasp_location(added_image, [[col, row]], angle, 
                            l = 20, r = 15, thickness = 2)
    
    if pwd is not None:
        save_img(added_image, pwd, name, title = title)

    return added_image

def plot_error(img, tomato_pred = None, tomato_act = None, error = None,
               pwd=None, 
               name=None, 
               use_mm = False,
               title="", 
               resolution=300, 
               title_size=20, ext = 'png'):

    fig, ax = plt.subplots()
    ax.imshow(img)    
    plt.rcParams["savefig.format"] = ext
    plt.rcParams["savefig.bbox"] = 'tight' 
    plt.rcParams['axes.titlesize'] = title_size
        
    plt.imshow(img)
    plt.axis('off')
    plt.title(title)
    
    if use_mm:
        unit = 'mm'
    else:
        unit = 'px'
    
    # https://stackoverflow.com/a/27227718
    plt.gca().set_axis_off()
    plt.subplots_adjust(top = 1, bottom = 0, right = 1, left = 0, 
        hspace = 0, wspace = 0)
    plt.margins(0,0)
    plt.gca().xaxis.set_major_locator(plt.NullLocator())
    plt.gca().yaxis.set_major_locator(plt.NullLocator())
    
    n_true_pos = len(tomato_pred['true_pos']['centers'])
    n_false_pos = len(tomato_pred['false_pos']['centers'])
    n_false_neg = len(tomato_act['false_neg']['centers'])
    if 'com' in tomato_pred.keys():
        n_com = len(tomato_pred['com'])
    else:
        n_com = 0
    
    centers = []
    centers.extend(tomato_pred['true_pos']['centers'])
    centers.extend(tomato_pred['false_pos']['centers']) 
    centers.extend(tomato_act['false_neg']['centers']) 
    if 'com' in tomato_pred.keys():
        centers.extend(tomato_pred['com'])
    
    labels = []
    labels.extend(['true_pos'] * n_true_pos)
    labels.extend(['false_pos'] * n_false_pos)
    labels.extend(['false_neg'] * n_false_neg)
    labels.extend(['com'] * n_com)
    
    error_centers = []
    error_centers.extend(error['centers'])
    error_centers.extend(n_false_pos * [None]) 
    error_centers.extend(n_false_neg * [None]) 
    if 'com' in tomato_pred.keys():
        error_centers.append(error['com'])

    if 'radii' in error.keys():
        error_radii_val = error['radii']
    else:
        error_radii_val = [None] * n_true_pos
    error_radii = []
    error_radii.extend(error_radii_val)
    error_radii.extend(n_false_pos * [None]) 
    error_radii.extend(n_false_neg * [None]) 
    error_radii.extend(n_com * [None])  
    
    # sort based on the y location of the centers
    zipped = zip(centers, error_centers, error_radii, labels)
    zipped.sort(key = lambda x: x[0][1])    
    centers, error_centers, error_radii, labels = zip(*zipped)
    
    # default bbox style
    bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="w", lw=0.72)
    kw_default = dict(arrowprops=dict(arrowstyle="-"),
              bbox=bbox_props, va="center", size = 12, color='k') 
        
    h, w = img.shape[:2]
    n = len(centers)+ 1
    y_text = 0 # 1.0/n* h
    for center, error_center, error_radius, label in zip(centers, error_centers, error_radii, labels):

        # copy default style
        kw = copy.deepcopy(kw_default)
            
        if label == 'true_pos':

            center_error = int(round(error_center))
            if error_radius is not None:
                radius_error = int(round(error_radius))
                text = 'loc: {c:d}{u:s} \nr: {r:d}{u:s}'.format(c=center_error, r= radius_error, u=unit)
            else:
                text = 'loc: {c:d}{u:s}'.format(c=center_error, u=unit)
            arrow_color = 'k'

        elif label == 'com':
            center_error = int(round(error_center))
            text = 'com: {c:d}{u:s}'.format(c=center_error, u=unit)
            
            kw['bbox']['fc'] = 'k'
            kw['bbox']['ec'] = 'k'
            kw['color']= 'w'       
            arrow_color = 'k'
            
        elif label == 'false_pos':
            
            text = 'false positive'
            kw['bbox']['fc'] = 'r'
            kw['bbox']['ec'] = 'r'
            # kw['color']= 'r'
            arrow_color = 'r'
            
        elif label == 'false_neg':
            
            text = 'false negative'
            kw['bbox']['ec'] = 'lightgrey'
            kw['bbox']['fc'] = 'lightgrey'
            arrow_color = 'lightgrey'
            
        y = center[1]
        x = center[0]
        
        if x <= 0.35*w:
            x_text = 0.6*w # -0.2*w
        elif x <= 0.5*w:
            x_text = 0.2*w *0.25 
        elif x <= 0.65*w:
            x_text = 0.8*w
        else: 
            x_text = 0.2*w  # w
            
        y_text = y_text + 1.0/n* h      
        
        x_diff = x_text - x
        y_diff = y_text - y
        if (x_diff > 0 and y_diff > 0) or (x_diff < 0 and y_diff < 0):
            ang = -45
        else:
            ang = 45      
        
        connectionstyle = "angle,angleA=0,angleB={}".format(ang)
        kw["arrowprops"].update({"connectionstyle": connectionstyle, 'color': arrow_color})
        plt.annotate(text, xy=(x, y), xytext=(x_text, y_text), **kw) #  


    if pwd:
        fig.savefig(os.path.join(pwd, name), dpi = resolution, bbox_inches='tight', pad_inches=0)

def add_contour(imRGB, mask, color = (255,255,255), thickness = 5):
    contours, hierarchy= cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[-2:]
    cv2.drawContours(imRGB, contours, -1, color, thickness)
    return imRGB

def compute_line_points(center, angle, l):
    ' angle in rad'
    col = center[0]
    row = center[1]
    
    col_start = col + 0.5*l*np.cos(angle)
    row_start = row + 0.5*l*np.sin(angle)
    
    col_end = col - 0.5*l*np.cos(angle)
    row_end = row - 0.5*l*np.sin(angle)
        
    start_point = (int(round(col_start)), int(round(row_start)))
    end_point = (int(round(col_end)), int(round(row_end)))
    return start_point, end_point

def add_lines(img_rgb, centers, angles, l =20, color = (255,255,255), thickness = 1, is_rad = True):
    'angle in rad'
    if isinstance(centers, (list, tuple)):  
        centers = np.array(centers, ndmin=2)          
        
    if not isinstance(angles, (list, tuple)):
        angles = [angles]
        
    for center, angle in zip(centers, angles):
        if not is_rad:
            angle = angle/180*np.pi
        start_point, end_point = compute_line_points(center, angle, l)

        cv2.line(img_rgb, start_point, end_point, color, thickness=thickness)
    
def add_arrows(img_rgb, centers, angles, l =20, color=(255,255,255), thickness = 1, tip_length = 0.5, is_rad = True):
    'angle in rad'
    if isinstance(centers, (list, tuple)):  
        centers = np.array(centers, ndmin=2)          
        
    if not isinstance(angles, (list, tuple)):
        angles = [angles]
        
    for center, angle in zip(centers, angles):
        if not is_rad:
            angle = angle/180*np.pi
        start_point, end_point = compute_line_points(center, angle, l)

        cv2.arrowedLine(img_rgb, start_point, end_point, color, thickness, tipLength = tip_length)
    
def plot_grasp_location(img_rgb, loc, angle, 
                        l = 30, 
                        r = 10, 
                        thickness = 2,
                        pwd= None, 
                        name = None, 
                        title = '',
                        ext= 'png', 
                        resolution = 300):

    'angle in rad'      
    loc = loc[0]          
            
    start_point, end_point = compute_line_points(loc, angle + np.pi/2, r)
        
    add_lines(img_rgb, start_point, angle, l = l,  color = (255,255,255), thickness = thickness)    
    add_lines(img_rgb, end_point, angle, l = l,  color = (255,255,255), thickness = thickness)
    # add_circles(img_rgb, loc, radii = r,  color = (255,255,255), thickness = -1)  

    if pwd is not None:
        save_img(img_rgb, pwd, name, title = title)
        
    return img_rgb
    
def pipi(angle):
    # cast angle to range [-180, 180]
    return (angle + 180) % 360 - 180    
    
def change_brightness(img, brightness):
    img_copy = img.copy()
    
    if brightness > 0 and brightness < 1:
        return img_copy + ((255  - img_copy)**brightness).astype(np.uint8) 
        
    if brightness > -1 and brightness < 0:
        return img_copy - ((img_copy)**-brightness).astype(np.uint8) 
        
    else:
        print 'I can not do anything with this brightness value!'
        return img
    
def plot_timer(timer_dict, N = 1, threshold = 0, ignore_key=None, pwd = None, name = 'time', title = 'time'):   
    
    for key in timer_dict.keys():
        
        # remove ignored keys
        if key == ignore_key:
            del timer_dict[key]
            continue
            
        # remove empty keys
        if timer_dict[key] == []:
            del timer_dict[key]
       
    values = np.array(timer_dict.values())
    
    if len(values.shape) == 1:
        values = values/N
    else:
        values = np.mean(values, axis = 1)
        
    labels = np.array(timer_dict.keys())   
    
    values_rel = values/np.sum(values)
    i_keep = (values_rel > threshold)
    i_remove = np.bitwise_not(i_keep)
    
    # if everything is put under others
    if np.all(i_remove == True):
        print("No time to plot!")
        return
    
    labels_keep = labels[i_keep].tolist()
    values_keep = values[i_keep].tolist() 
    
    if np.any(i_remove == True):
        remains = np.mean(values[i_remove])
        values_keep.append(remains)
        labels_keep.append('others')


    l = zip(values_keep, labels_keep)
    l.sort()
    values_keep, labels_keep = zip(*l)
    
    donut(values_keep, labels_keep, pwd = pwd, name = name, title = title)

#    fig, ax = plt.subplots()
#    ax.pie(values_keep, labels=labels_keep, autopct=make_autopct(values_keep), startangle=90, labeldistance=1.2)
#    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
#    
#    fig.show()

def donut(data, labels, pwd = None, name = None, title = None):
    data = np.array(data)
    data_rel = data/sum(data)*100    
    
    text = []
    separator = ': '
    for label, value, value_rel in zip(labels, data, data_rel):
        text.append(label + separator + str(int(round(value_rel))) + '% (' + str(int(round(value))) + ' ms)')
    
    fig, ax = plt.subplots(figsize=(6, 3), subplot_kw=dict(aspect="equal"))
    
    
    
    wedges, texts = ax.pie(data, wedgeprops=dict(width=0.5), startangle=-45)
    
    bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
    kw = dict(arrowprops=dict(arrowstyle="-"),
              bbox=bbox_props, zorder=0, va="center")
    
    for i, p in enumerate(wedges):
        ang = (p.theta2 - p.theta1)/2. + p.theta1
        y = np.sin(np.deg2rad(ang))
        x = np.cos(np.deg2rad(ang))
        horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
        connectionstyle = "angle,angleA=0,angleB={}".format(ang)
        kw["arrowprops"].update({"connectionstyle": connectionstyle})
        ax.annotate(text[i], xy=(x, y), xytext=(1.35*np.sign(x), 1.4*y),
                    horizontalalignment=horizontalalignment, **kw)
    
    ax.set_title(title)

    if pwd is not None:
        save_fig(fig, pwd, name)
    
def make_autopct(values):
    def my_autopct(pct):
        total = sum(values)
        val = int(round(pct*total/100.0)) # [ms]
        return '{p:.2f}%  ({v:d} ms)'.format(p=pct,v=val)
    return my_autopct
    
def angular_difference(x, y):
    '''
    compute the difference between two angles x, y
    '''
    return np.abs(np.arctan2(np.sin(x-y), np.cos(x-y)))