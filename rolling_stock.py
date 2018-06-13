#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 28 08:52:38 2018

@author: Walthall
"""
from constants import gravity
temperature = 20 #degrees Celsius
#import route
import density
import os, csv
#import numpy as np
#import matplotlib.pyplot as plt
import time as tm

start_time = tm.time()


class Rolling_stock(object):
    
    def position(self,position_in_train):
        '''
        define the railcar's position in the trainset as an integer
        0 denotes the leading unit (typically a locomotive)
        '''
        self.position = position_in_train
        
        if self.position == 0:
            self.drag_coefficient = 'drag at front'
    
    def calculate_location(self,train,path):
        #determine the location of the front of the railcar along the route
        #x starts as the location of the front of the train along the path
        x = train.location
        for k in range(0,self.position):
            #each element of the train has a length attribute
            #we're assuming the lengths of the couplings are included in the 
            #lengths of each element
            x -= train.consist[k].length
        #x is now the location of the front of the car
        self.location = x
        
        #we're assuming only two trucks per element, and that the car is symetric
        #this will need to be adapted for articulated railcars
        self.front_truck_location = self.location - (self.length 
                                                - self.truck_spacing)/2
        self.rear_truck_location  = self.location - (self.length 
                                                + self.truck_spacing)/2

        
    def calculate_grade_resistance(self, path):
        #calculate the railcar's inclination
        self.inclination = ((path.elevation(self.front_truck_location) 
                            - path.elevation(self.rear_truck_location))
                            /self.truck_spacing)
        #calculate the railcar's grade resistance in Newtons
        self.grade_resistance = gravity * self.inclination * (self.gross*1000)
        
    def calculate_curve_resistance(self, path):
        #calculate the curve resistance in Newtons
        self.curve_resistance = (0.0004 * gravity * self.gross * 
                                 (path.curvature(self.front_truck_location) + 
                                  path.curvature(self.rear_truck_location))/2)
        
    def calculate_internal_resistance(self,train,internal = 0):
        '''
        the internal resistance from generators, i.e. on passenger or 
        refrigeration cars
        
        for now, we'll consider four cases:
            no internal power requirements (default)
            'small' generator providing 4kW
            'big' generator providing 15kW
            head-end power ('HEP') provided by the locomotive requiring 5kW
        '''
    
        if   internal == 'big' or internal == '15kW':
            self.internal_resistance = ((59.2/((train.speed*2.23693)**0.925))
                                        *4.903*self.gross)
            self.HEP = 0
        elif internal == 'small' or internal == '4kW':
            self.internal_resistance = ((87.5/((train.speed*2.23693)**0.940))
                                        *4.903*self.gross)
            self.HEP = 0
        elif internal == 'HEP':
            self.internal_resistance = 0
            self.HEP = 5 #kW
        else:
            self.internal_resistance = 0
            self.HEP = 0
    
    def calculate_rolling_resistance(self):
        #conversion factor from lbf to N
        lbf_N = 4.44822 #N/lbf
        #conversion factor from tons to tonnes
        ton_tonne = 0.907185 #tonnes/ton
        
        #Canadian National
        def A_CN(w):
            axle_load_ton = w/ton_tonne
            return (1.5 + 18/axle_load_ton)*lbf_N/ton_tonne
        #original Davis
        def A_Davis(w):
            return 6.4 +157/w
        #modified Davis
        def A_Davis_mod(w):
            axle_load_ton = w/ton_tonne
            return (0.6 + 20/axle_load_ton)*lbf_N/ton_tonne
        #Davis formula for very light axle loads
        #not currently used
        def A_Davis_lt(w):
            return (48.4/(w**0.5) + 67.6/w)
        
        if resistance_method == 'Davis':
            self.rolling_resistance = A_Davis(self.w)*self.gross
        elif resistance_method == 'Davis_mod':
            self.rolling_resistance = A_Davis_mod(self.w)*self.gross
        else:
            self.rolling_resistance = A_CN(self.w)*self.gross

    
    def calculate_flange_resistance(self, train):
        #conversion factor from lbf to N
        lbf_N = 4.44822 #N/lbf
        #conversion factor from tons to tonnes
        ton_tonne = 0.907185 #tonnes/ton
        #conversion factor from mph to m/s
        mph_ms = 0.4470
        
        #Canadian National
        def B_CN():
            return 0.03*(train.speed/mph_ms)*lbf_N/ton_tonne
        
        def B_Davis():
            return 0.045*(train.speed/mph_ms)*lbf_N/ton_tonne
        
        def B_Davis_mod():
            return 0.01*(train.speed/mph_ms)*lbf_N/ton_tonne
        
        if resistance_method == 'Davis':
            self.flange_resistance = B_Davis()*self.gross
        elif resistance_method == 'Davis_mod':
            self.flange_resistance = B_Davis_mod()*self.gross
        else:
            self.flange_resistance = B_CN()*self.gross
    
    def calculate_air_resistance(self, train, path):
        #conversion factor from lbf to N
        lbf_N = 4.44822 #N/lbf
        #conversion factor from mph to m/s
        mph_ms = 0.4470

        def C_CN():
            C = air_coefficients[self.type]['C']
            a = air_coefficients[self.type]['a']
            return (C*a*((train.speed/mph_ms)**2)/10000)*lbf_N
        
        density_adjustment = (density.density_h(path.elevation(self.location),
                                                temperature)/
                              density.density_h(0,20))

        if resistance_method == 'CN':
            self.air_resistance = C_CN()
        
        self.air_resistance *= density_adjustment
    
    def calculate_total_resistance(self):
        self.R = (self.grade_resistance + 
                  self.curve_resistance + 
                  self.internal_resistance + 
                  self.rolling_resistance + 
                  self.flange_resistance + 
                  self.air_resistance)
    
    def initialise_resistances(self, train, path):
        '''
        call this function to initialise the railcar's resistances
        '''
        self.calculate_grade_resistance(path) #changes with location
        self.calculate_curve_resistance(path) #changes with location
        self.calculate_internal_resistance(train) #only changes for specific car types if the velocity changes
        self.calculate_rolling_resistance() #only changes if the load changes
        self.calculate_flange_resistance(train) #changes with velocity
        self.calculate_air_resistance(train,path) #changes with velocity and location
        
        self.calculate_total_resistance()
    
    def update_resistance_for_location(self, train, path):
        '''
        call this function to update the railcar's resistances if the location
            changes, but not the velocity
        '''
        self.calculate_grade_resistance(path)
        self.calculate_curve_resistance(path)
        self.calculate_air_resistance(train, path)
        
        self.calculate_total_resistance()
    
    def update_resistance(self, train, path):
        '''
        call this function to update the resistances in general
        This will handle changes in velocity
        '''
        self.calculate_grade_resistance(path)
        self.calculate_curve_resistance(path)
        self.calculate_internal_resistance(train)
        self.calculate_flange_resistance(train)
        self.calculate_air_resistance(train, path)
        
        self.calculate_total_resistance()
        
    def air_brake(self, train, path):
#        if train.emergency_brake:
#            #the emergency air brake is generally 20-30% stronger than the 
#                #service air brake, according to 
#                #en.wikipedia.org/wiki/Railway_air_brake
#            #for now we'll use the upper value of the friction coefficient from Hay
#            pass
        def friction_coefficient(v):
            def linear_interpolation(x, x1, x2, y1, y2):
                m = (y2 - y1)/(x2 - x1) #slope is rise over run
                return y1 + m*(x - x1)
    
            friction_coefficient_values = [ #expressed as percentages
                    48.80597015,
                    37.14285714,
                    31.71428571,
                    28.97058824,
                    27.20588235,
                    25.88235294,
                    24.85294118,
                    24.70588235,
                    24.55882353,
                    24.41176471]
            friction_coefficient_speeds = [  #in kilometres per hour
                    0.0,
                    16.0934,
                    32.1868,
                    48.2802,
                    64.3736,
                    80.467,
                    96.5604,
                    112.6538,
                    128.7472,
                    144.8406]
            
            if v > friction_coefficient_speeds[-1]:
                f1 = friction_coefficient_values[-2]
                f2 = friction_coefficient_values[-1]
                v1 = friction_coefficient_speeds[-2]
                v2 = friction_coefficient_speeds[-1]
            else:
                for k in range(len(friction_coefficient_values) - 1):
                    if v >= friction_coefficient_speeds[k]:
                        if v < friction_coefficient_speeds[k + 1]:
                            f1 = friction_coefficient_values[k]
                            f2 = friction_coefficient_values[k + 1]
                            v1 = friction_coefficient_speeds[k]
                            v2 = friction_coefficient_speeds[k + 1]
                            break

            return linear_interpolation(v,v1,v2,f1,f2)/100
        
        if train.emergency_brake:
            train.service_level == 1.0
        
        if train.service_level == 0:
            self.air_brake_force = 0
        else:
            #The friction coefficient should determine the maximum breaking potential for a full-service brake
            # we will assume that the railcar is designed to apply x% of its tare weight at maximum friction coefficient
            self.air_brake_force = (gravity * 1000 * self.tare * path.adhesion
                                    * self.brake_percent 
                                    * friction_coefficient(train.speed)
                                    /friction_coefficient(0))*train.service_level
        if train.emergency_brake:
            self.air_brake_force *= 1.3

    def calculate_brake_force(self,train,path):
        self.air_brake(train,path)
        self.brake_force = self.air_brake_force

#set to 'CN' for Canadian Nation, 'Davis' for original Davis, or Davis_mod for 
#modified Davis
#will use 'CN' by default
resistance_method = 'CN'
if resistance_method == 'CN':
    #import the CN air resistance values
    #go to the proper folder
    os.chdir('..')
    os.chdir('Data')
    
    air_coefficients = {}
    with open('CN_airResistance.csv', 'r') as csvfile:
        f = csv.reader(csvfile, delimiter = ',')
        next(f, None)
        for row in f:
            air_coefficients[row[0]] = {
                    'C': float(row[1]),
                    'a': int(row[2])
                    }
        
    #go back to the code directory
    os.chdir('..')
    os.chdir('Code')
#the CN data does not currently include intermodal double stacks
#we'll assume the following values, based on a closed Auto transporter
air_coefficients['Intermodal double-stack'] = {
        'C': 7.1,
        'a': 170}


    







'''
speeds = np.linspace(0,120,1000)
BF_electric = []
BF_diesel = []
for k in speeds:
    BF_electric.append(dynamic_braking_force_electric(k))
    BF_diesel.append(dynamic_braking_force_diesel(k))
BF_electric = np.array(BF_electric)
BF_diesel = np.array(BF_diesel)


fig2 = plt.figure(figsize=(8, 6.5))
fig2.suptitle("Dynamic Braking Characteristics", fontsize = 16)
ax3 = fig2.add_subplot(211)
plt.title("Electric locomotive (regenerative braking)")
ax3.plot(speeds,BF_electric)
plt.xlim(0,120)
plt.ylim(0,250)
ax3.grid(True, axis = 'y')
plt.ylabel("Braking force (kN)")

ax4 = fig2.add_subplot(212)
plt.title("Diesel-electric locomotive (rheostatic barking)")
ax4.plot(speeds,BF_diesel)
plt.xlim(0,120)
plt.ylim(0,250)
ax4.grid(True, axis = 'y')
plt.ylabel("Braking force (kN)")
plt.xlabel("velocity (kph)")
plt.tight_layout()
plt.subplots_adjust(hspace=0.4, top = 0.9)



ax3.annotate('field limited',
            xy=(7.5, dynamic_braking_force_electric(7.5)), xycoords='data',
            xytext=(50, -30), textcoords='offset points',
            arrowprops=dict(arrowstyle="->",
                            connectionstyle="arc3,rad=-.1"))
ax3.annotate('current limited',
            xy=((50+15)/2, dynamic_braking_force_electric((50+15)/2)),
            xycoords='data',
            xytext=(5, -40), textcoords='offset points',
            arrowprops=dict(arrowstyle="->",
                            connectionstyle="arc3,rad=-.1"))
ax3.annotate('voltage limited',
            xy=(65, dynamic_braking_force_electric(65)), xycoords='data',
            xytext=(-5, -60), textcoords='offset points',
            arrowprops=dict(arrowstyle="->",
                            connectionstyle="arc3,rad=-.1"))
ax3.annotate('commutator\nlimited',
            xy=(100, dynamic_braking_force_electric(100)), xycoords='data',
            xytext=(0, 15), textcoords='offset points',
            arrowprops=dict(arrowstyle="->",
                            connectionstyle="arc3,rad=-.1"))

ax4.annotate('limited by current\nand heat dissipation',
            xy=((50+15)/2 + 2, dynamic_braking_force_diesel((50+15)/2 + 2)), 
            xycoords='data',
            xytext=(5, -30), textcoords='offset points',
            arrowprops=dict(arrowstyle="->",
                            connectionstyle="arc3,rad=-.1"))
'''
'''
ax4.annotate('90% max speed\nafter 10.5 minutes',
            xy=(10.5, velocities[63]), xycoords='data',
            xytext=(100, -30), textcoords='offset points',
            arrowprops=dict(arrowstyle="->",
                            connectionstyle="arc3,rad=-.1"))
'''

'''
plt.savefig("dynamic braking characteristics",dpi = 330)
plt.show()



print (tm.time() - start_time)

#plt.plot(locations/1000, velocities)
#plt.show(0)
'''