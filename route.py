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
        return 200
    def curvature(self,x):
        return 0
    def track_class(self,x):
        self.speed_limit = 60*1.6
        self.adhesion = 0.30
    

