#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 15:49:29 2020

@author: jelle
"""

import rospy
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped

class PoseTransform(object):
    """PoseTransform"""
    def __init__(self):
        self.event = None
        self.object_pose = None
        
        rospy.init_node("Object_Detection",
                        anonymous=True, log_level=rospy.DEBUG)
        
        self.pose_cb_lambda = lambda msg: self.pose_cb(msg, self)
        rospy.Subscriber("Object_Detection/objectPose", 
                         PoseStamped, self.pose_cb_lambda)
        
        self.e_in_cb_lambda = lambda msg: self.e_in_cb(msg, self)
        rospy.Subscriber("~e_in", 
                         String, self.e_in_cb_lambda)
        
        self.pub_pose = rospy.Publisher('~endEffectorPose',
                                        PoseStamped, queue_size=5, latch=True)
        
        self.pub_e_out = rospy.Publisher("~e_out",
                                         String, queue_size=10, latch=True)
        
    def pose_cb(msg, self):
        if self.object_pose is None:
            self.object_pose = msg
            rospy.logdebug("Received new move robot pose message")
            
    def e_in_cb(msg, self):
        if self.event is None:
            self.event = "e_start"
            rospy.logdebug("Received new move robot event message")
            
    def transform_pose(self):
        if self.event == "e_start":
            msg_pose = self.object_pose
            msg_e = String
            msg_e.data = "e_success"
            
            self.pub_pose(msg_pose)
            self.pub_e_out(msg_e)
            
            self.object_pose = None
            self.event = None
        
            
def main():
    try:
        PT = PoseTransform()
        rate = rospy.Rate(10)
        while not rospy.core.is_shutdown():
            PT.transform_pose()
            rate.sleep()

    except rospy.ROSInterruptException:
        return
    except KeyboardInterrupt:
        return
    
if __name__ == '__main__':
    main()
        
        