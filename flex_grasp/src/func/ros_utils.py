#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Fri May 15 12:56:46 2020

@author: taeke
"""

import rospy

# messages
from std_msgs.msg import String


def wait_for_success(topic, timeout):


    start_time = rospy.get_time()
    curr_time = rospy.get_time()

    # rospy.logdebug("==WAITING FOR SUCCESS==")
    # rospy.logdebug("start time: %s", start_time)
    # rospy.logdebug("current time: %s", curr_time)
    while (curr_time - start_time < timeout) and not rospy.is_shutdown():
        # rospy.logdebug("current time: %s", curr_time)
        try:
            message = rospy.wait_for_message(topic, String, timeout)
            if message.data == "e_success":
                rospy.logdebug("Command succeeded: received %s on topic %s", message.data, topic)
                return True
            elif message.data == "":
                pass
            else:
                rospy.logwarn("Command failed: node returned %s on topic %s", message.data, topic)
                return False
        except:
            rospy.logwarn("Command failed: timeout exceeded while waiting for message on topic %s", topic)
            return False

        rospy.sleep(0.2)
        curr_time = rospy.get_time()

    if rospy.is_shutdown():
        pass
    else:
        rospy.logwarn("Command failed: node did not return success within timeout on topic %s", topic)
    return False