#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 28 09:45:20 2018

@author: Walthall



with a given set of points along the route, interpolate the route of the train
this means that parabolic vertical curves and spiral horizontal curves should
be created to fit the points along the route
"""

class Route(object):
    #starting with a flat, straight track
    def __init__(self,length):
        self.length = length
    def elevation(self,x):
        if x < 50000:
            return 200 + 0.01*x
        else:
            return 200 + 0.01*50000 - 0.01*(x - 50000)
    def curvature(self,x):
        return 0
    def track_class(self,x):
        self.speed_limit = 60*1.6
        self.adhesion = 0.30
    
    def current_speed_limit(self,x):
        self.speed_limit = 60*1.6
    
    def determine_speed_limit(self,x):
        return 40*1.6/3.6
    
    def track_adhesion(self,x):
        self.adhesion = 0.30
    

