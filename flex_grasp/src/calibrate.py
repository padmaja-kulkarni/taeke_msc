#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu May 14 14:28:49 2020

@author: taeke
"""

import rospy
import numpy as np

# messages
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped, PoseArray, Pose

import tf2_ros # for error messages
import tf2_geometry_msgs

from easy_handeye.handeye_client import HandeyeClient


# custom functions
from func.ros_utils import wait_for_success
from func.conversions import list_to_position, list_to_orientation

class Calibrate(object):
    """Calibrate"""
    def __init__(self):    

        self.debug_mode = rospy.get_param("calibrate/debug")
        
        if self.debug_mode:
            log_level = rospy.DEBUG
        else:
            log_level = rospy.INFO
        
        rospy.init_node("move_robot",
                anonymous=True,
                log_level=log_level)
        
        if self.debug_mode:
            rospy.loginfo("[CALIBRATE] Luanching calibrate in debug mode")
        

        rospy.sleep(5)
        
        # rospy.loginfo("[CALIBRATE] initializing hand eye client")
        # self.client = HandeyeClient()
        
        # Listen
        rospy.loginfo("[CALIBRATE] initializing tf2_ros buffer")
        self.tfBuffer = tf2_ros.Buffer()
        self.listener = tf2_ros.TransformListener(self.tfBuffer)
        
        
        self.calibration_frame = "px150/base_link"
        self.planning_frame = "world"
        self.pose_array = None
        
        # rospy.Subscriber("/aruco_tracker/pose", PoseStamped, self.aruco_tracker_cb)
    
        self.pub_move_robot_command = rospy.Publisher("move_robot/e_in",
                                  String, queue_size=10, latch=True)
        
        self.pub_move_robot_pose = rospy.Publisher("pre_grasp_pose",
                                  PoseStamped, queue_size=10, latch=True)
        
        self.pub_pose_array = rospy.Publisher("pose_array",
                                PoseArray, queue_size=5, latch=True)
        
        
    # def aruco_tracker_cb(self, msg):
    #     pass
        
    def init_poses(self):
        pose_array = PoseArray()
        pose_array.header.frame_id = self.calibration_frame
        pose_array.header.stamp = rospy.Time.now()
        
        x_amplitude = 0.05
        y_amplitude = 0.08
        z_amplitude = 0.05
        
        x_min = 0.25
        y_min = -y_amplitude
        z_min = 0.08 # 0.05

        
        intervals = 3
        x_vec = np.linspace(x_min, x_min + 2*x_amplitude, intervals)
        y_vec = np.linspace(y_min, y_min + 2*y_amplitude, intervals)
        z_vec = np.linspace(z_min, z_min + 2*z_amplitude, intervals)
        
        ai_amplitude = 20.0/180*np.pi
        aj_amplitude = 20.0/180*np.pi
        
        ai_vec = np.linspace(-ai_amplitude, ai_amplitude, intervals)
        aj_vec = np.linspace(-aj_amplitude, aj_amplitude, intervals)
        
        poses = []
        
        for x in x_vec:
            for y in y_vec:
                for z in z_vec:
                    for aj in aj_vec:
                        for ai in ai_vec:
                            pose = Pose()
                            pose.position = list_to_position([x, y, z])
                            
                            ak = np.arctan(y/x)
                            pose.orientation = list_to_orientation([ai, aj, ak])
                            
                            poses.append(pose)
                    
        pose_array.poses = poses
        self.pose_array = pose_array
        
    def go_to_poses(self):
        
        # does pose array contain something?
        if self.pose_array is None:
            rospy.logwarn("[CALIBRATE] pose_array is still empty")
            return False
        
        try:
            trans = self.tfBuffer.lookup_transform(self.planning_frame,self.pose_array.header.frame_id,  rospy.Time(0))
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException):
            rospy.logwarn("[CALIBRATE] failed to get transform from %s to %s", self.pose_array.header.frame_id, self.planning_frame)
            return False

        
        for pose in self.pose_array.poses:
            if rospy.is_shutdown():
                return False
            
            pose_stamped = PoseStamped()
            pose_stamped.header = self.pose_array.header
            pose_stamped.pose = pose
            
            
            pose_trans = tf2_geometry_msgs.do_transform_pose(pose_stamped, trans)
            
            
            
            self.pub_move_robot_pose.publish(pose_trans)
            self.pub_move_robot_command.publish("move")
            
            # get response
            success = wait_for_success("move_robot/e_out", 5)
        
            if success:
                # wait a small amount of time for vibrations to stop
                rospy.sleep(0.1)
                # sample_list = self.client.take_sample()
                # rospy.loginfo("taking sample, sample list: %s", sample_list)

        # rospy.loginfo("computing calibration")
        # result = self.client.compute_calibration()
        # rospy.loginfo("result: %s", result)
        # self.client.save()
        return True




def main():
    try:
        
        calibrate = Calibrate()
        rate = rospy.Rate(1)
        
        calibrate.init_poses()
        calibrate.pub_pose_array.publish(calibrate.pose_array)
        
        rospy.sleep(10)
        
        success = calibrate.go_to_poses()
        if success:
            rospy.loginfo("Calibration finished succesfully")
        else:
            rospy.logwarn("Calibration failed")
        
        while not rospy.core.is_shutdown():
            rate.sleep()

    except rospy.ROSInterruptException:
        return
    except KeyboardInterrupt:
        return

if __name__ == '__main__':
    main()
