#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 15:30:31 2020

@author: jelle
"""

import numpy as np
import rospy
import cv2
import json
from cv_bridge import CvBridge

# msg
from sensor_msgs.msg import Image
from geometry_msgs.msg import PoseStamped
from flex_grasp.msg import Tomato, Truss, Peduncle, ImageProcessingSettings
from depth_interface import DepthImageFilter, PointCloudFilter

from flex_vision.detect_truss.ProcessImage import ProcessImage

from flex_shared_resources.utils.conversions import point_to_pose_stamped, settings_lib_to_msg, settings_msg_to_lib
from func.utils import camera_info2rs_intrinsics
from func.utils import colored_depth_image


from flex_grasp.msg import FlexGraspErrorCodes
import os

DEFAULT_PUBLISH_SEGMENTS = False


class ObjectDetection(object):
    """ObjectDetection"""

    def __init__(self, node_name):

        self.node_name = node_name

        # frames
        self.camera_frame = "camera_color_optical_frame"

        # data
        self.color_image = None
        self.depth_image = None
        self.color_info = None
        self.pcl = None

        # params
        self.patch_size = 5
        self.peduncle_height = 0.080  # [m]
        self.settings = None

        self.bridge = CvBridge()
        self.pwd_data = None
        self.id = None

        self.process_image = ProcessImage(name='ros_tomato', pwd='', save=False)

        settings = settings_lib_to_msg(self.process_image.get_settings())

        # Publish
        self.pub_truss_pose = rospy.Publisher("truss_pose", PoseStamped, queue_size=5, latch=True)
        self.pub_object_features = rospy.Publisher("object_features", Truss, queue_size=5, latch=True)
        self.pub_tomato_image = rospy.Publisher("tomato_image", Image, queue_size=5, latch=True)
        self.pub_depth_image = rospy.Publisher("depth_image", Image, queue_size=5, latch=True)
        # self.pub_color_hue = rospy.Publisher("color_hue", Image, queue_size=5, latch=True)
        # self.pub_peduncle_pcl = rospy.Publisher("peduncle_pcl", PointCloud2, queue_size=10, latch=True)
        # self.pub_tomato_pcl = rospy.Publisher("tomato_pcl", PointCloud2, queue_size=10, latch=True)

        pub_image_processing_settings = rospy.Publisher("image_processing_settings",
                                                        ImageProcessingSettings, queue_size=10, latch=True)

        pub_image_processing_settings.publish(settings)

        # Subscribe
        rospy.Subscriber("image_processing_settings", ImageProcessingSettings, self.image_processing_settings_cb)

    @property
    def pwd_data(self):
        return self.__pwd_data

    @pwd_data.setter
    def pwd_data(self, new_path):
        """With this setter the user will always get an update when the path is changed"""

        self.__pwd_data = new_path
        if self.pwd_data is not None:
            rospy.loginfo("[{0}] Storing results in folder {1}".format(self.node_name, new_path))

    def image_processing_settings_cb(self, msg):
        self.settings = msg
        rospy.logdebug("[{0}] Received image processing settings".format(self.node_name))

    def save_data(self, result_img=None):
        """Save visual data"""

        # information about the image which will be stored
        image_info = {}
        image_info['px_per_mm'] = self.compute_px_per_mm()
        json_pwd = os.path.join(self.pwd_data, self.id + '_info.json')

        rgb_img = self.color_image
        depth_img = colored_depth_image(self.depth_image.copy())

        with open(json_pwd, "w") as write_file:
            json.dump(image_info, write_file)

        self.save_image(rgb_img, self.pwd_data,  name=self.id + '_rgb.png')
        self.save_image(depth_img, self.pwd_data, name=self.id + '_depth.png')
        if result_img is not None:
            result = self.save_image(result_img, self.pwd_data, name=self.id + '_result.png')

        imgmsg_depth = self.bridge.cv2_to_imgmsg(depth_img, encoding="rgb8")
        self.pub_depth_image.publish(imgmsg_depth)
        return result

    def save_image(self, img, pwd, name):
        """Save image to the given path, if the path does not exist create it."""
        full_pwd = os.path.join(pwd, name)

        # Make sure the folder exists
        if not os.path.isdir(pwd):
            rospy.loginfo("[{0}]New path, creating a new folder {1}".format(self.node_name, pwd))
            os.mkdir(pwd)

        if cv2.imwrite(full_pwd, cv2.cvtColor(img, cv2.COLOR_RGB2BGR)):
            rospy.logdebug("[{0}] Successfully saved image to path {1}".format(self.node_name, full_pwd))
            return FlexGraspErrorCodes.SUCCESS
        else:
            rospy.logwarn("[{0}] Failed to save image to path %s".format(self.node_name, full_pwd))
            return FlexGraspErrorCodes.FAILURE

    def detect_object(self, save_result=True):
        """Detrect object"""
        px_per_mm = self.compute_px_per_mm()
        self.process_image.add_image(self.color_image, px_per_mm=px_per_mm)

        if self.settings is not None:
            self.process_image.set_settings(settings_msg_to_lib(self.settings))

        if not self.process_image.process_image():
            rospy.logwarn("[OBJECT DETECTION] Failed to process image")
            return FlexGraspErrorCodes.FAILURE

        object_features = self.process_image.get_object_features()
        tomato_mask, peduncle_mask, _ = self.process_image.get_segments()

        cage_pose = self.generate_cage_pose(object_features['grasp_location'], peduncle_mask)
        truss_visualization = self.process_image.get_truss_visualization(local=True)
        img_depth = colored_depth_image(self.depth_image.copy())

        if save_result:
            self.save_data(result_img=truss_visualization)

        # publish results tomato_img
        truss_visualization = self.bridge.cv2_to_imgmsg(truss_visualization, encoding="rgba8")
        imgmsg_depth = self.bridge.cv2_to_imgmsg(img_depth, encoding="rgb8")

        self.pub_tomato_image.publish(truss_visualization)
        self.pub_depth_image.publish(imgmsg_depth)
        if cage_pose is False:
            return FlexGraspErrorCodes.FAILURE
        self.pub_truss_pose.publish(cage_pose)
        return FlexGraspErrorCodes.SUCCESS

    def generate_cage_pose(self, grasp_features, peduncle_mask):
        row = grasp_features['row']
        col = grasp_features['col']
        angle = grasp_features['angle']
        if angle is None:
            rospy.logwarn("Failed to compute caging pose: object detection returned None!")
            return False

        # orientation
        rospy.logdebug("[{0}] Object angle in degree {1}".format(self.node_name, np.rad2deg(angle)))
        rpy = [0, 0, angle]

        rs_intrinsics = camera_info2rs_intrinsics(self.color_info)
        depth_image_filter = DepthImageFilter(self.depth_image, rs_intrinsics, patch_size=5, node_name=self.node_name)
        depth_assumption = self.get_table_height() - self.peduncle_height
        depth_measured = depth_image_filter.get_depth(row, col)

        # location
        rospy.loginfo("[{0}] Depth based on assumptions: {1:0.3f} [m]".format(self.node_name, depth_assumption))
        rospy.loginfo("[{0}] Depth measured: {1:0.3f} [m]".format(self.node_name, depth_measured))

        xyz = depth_image_filter.deproject(row, col, depth_assumption)

        if np.isnan(xyz).any():
            rospy.logwarn("[{0}] Failed to compute caging pose, will try based on segment!".format(self.node_name))
            xyz = depth_image_filter.deproject(row, col, segment=peduncle_mask)

            if np.isnan(xyz).any():
                rospy.logwarn("[{0}] Failed to compute caging pose!".format(self.node_name))
                return False

        return point_to_pose_stamped(xyz, rpy, self.camera_frame, rospy.Time.now())

    def get_table_height(self):
        """Estimate the distance between the camera and table"""
        point_cloud_filter = PointCloudFilter(self.pcl, patch_size=5, node_name=self.node_name)
        heights = point_cloud_filter.get_points(field_names="z")
        return np.nanmedian(np.array(heights))

    def compute_px_per_mm(self):
        """Estimate the amount of pixels per mm"""
        height = self.get_table_height()
        fx = self.color_info.K[0]
        fy = self.color_info.K[4]
        f = (fx + fy) / 2
        px_per_mm = f / height / 1000.0

        rospy.logdebug('[{0}] Distance between camera and table: {1:0.3f} [m]'.format(self.node_name, height))
        rospy.logdebug('[{0}] Pixels per mm: {1:0.3f} [px/mm]'.format(self.node_name, px_per_mm))
        return px_per_mm
