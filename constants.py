#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 12 10:27:36 2018

@author: Walthall
"""

'''
physical constants
'''
#gravitational constant
gravity = 9.80665 #m/s^2


'''
simulation constants
'''
#timestep for the simulation - make smaller for increased precision, larger for
    #faster simulations
timestep = 1.0 #s


'''
behavioural constants
'''
#when the train reaches a speed of (desired_speed - lower_threshold), it will 
#not continue to increase the throttle
lower_threshold = 1 #m/s

#when the train reaches a speed of (desired_speed - upper_threshold), it will
#lower the throttle
upper_threshold = 0.5 #m/s

#how far ahead does the train check for changes in grade and speed limits?
lookahead = 3000 #m

'''
mechanical constants
'''
dynamic_brake_increment = 0.05
air_brake_increment = 0.20