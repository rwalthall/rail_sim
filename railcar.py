#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 12 10:24:12 2018

@author: Walthall
"""

from rolling_stock import Rolling_stock

class Railcar(Rolling_stock):
    
    def __init__(self, car_type, length, axles, tare_weight, truck_spacing):
        self.length = length #m
        self.axles = axles
        self.tare = tare_weight #tonnes
        if truck_spacing == 'unknown':
            self.truck_spacing = length * 0.72
        else:
            self.truck_spacing = truck_spacing
        self.type = car_type
        
        self.brake_percent = 0.70
        
    
    def loading(self,load):
        '''
        define the load on the railcar
        in tonnes
        '''
        self.load = load
        self.gross = self.tare + load
        self.w = self.gross/self.axles
