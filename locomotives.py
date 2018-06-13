#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 12 10:20:06 2018

@author: Walthall
"""

from rolling_stock import Rolling_stock
from constants import gravity

import math


class Locomotive(Rolling_stock):
    
    def __init__(self, length, axles, weight, power, traction, truck_spacing):
        self.length = length
        self.axles = axles
        self.weight = weight
        self.tare = weight
        self.max_power = power
        self.traction = traction
        self.maximum_tractive_effort = traction
        self.truck_spacing = truck_spacing
        self.type = 'Leading Freight Locomotive'
        
        self.w = self.weight/self.axles
        
        self.gross = self.weight
        
        self.max_throttle = 8
        self.current_throttle = 0
        self.power = self.max_power * (self.current_throttle/self.max_throttle)**2
        
        self.brake_percent = 0.90
    
    def throttle(self, throttle_position):
        self.throttle_position = throttle_position
        self.power = (self.max_power 
                      * (self.throttle_position/self.max_throttle)**2) #squared because the throttle notches are current based, see Iwnicki pp. 255-6
    
    def tractive_effort(self, path, train):
        adhesion_limit = self.weight * 1000 * gravity * path.adhesion
        
        power_limit = self.max_power/train.speed
        
        Max_traction = 415000
        torque_reduction = (Max_traction - 360000)/(28/3.6) #approximated from figure 9.28 of Iwnicki
        current_limit = Max_traction - train.speed * torque_reduction
        
        self.traction = min(adhesion_limit, power_limit, current_limit)
        
        if self.traction == adhesion_limit:
            self.traction_limiting_factor = "Adhesion"
        elif self.traction == power_limit:
            self.traction_limiting_factor = "Power"
        else:
            self.traction_limiting_factor = "Motor"
            
        #thermal adjustment - Tractive effort thermal derating curve
        
        derating = math.exp(train.run_time/(200*60)*math.log(270000/Max_traction))
        self.traction *= derating
    
    def power_rate_application_limit(self):
        #see Iwnicki, pp. 256-7
        pass

    def rheostatic_dynamic_brake(self, train, path):
        #for diesel-electric locomotives, or electric locomotives that do not have 
            #adequate capacity for power return
        #based on figure 9.31 on page 259 of Iwnicki's Handbook
        #velocity in kph, braking force in kN
        
        def linear_interpolation(x, x1, x2, y1, y2):
            m = (y2 - y1)/(x2 - x1) #slope is rise over run
            return y1 + m*(x - x1)
        
        #points of velocity vs force in the field and current limited regimes
        v_points = [0.0,
                    13.41176471,
                    20.0,
                    27.07317073,
                    31.70731707,
                    39.02439024,
                    43.61445783,
                    51.08433735]
        F_points = [0.0,
                    231.6666667,
                    171.1864407,
                    233.3333333,
                    198.3050847,
                    235.8333333,
                    208.3333333,
                    236.6666667]
        
        def voltage_limited_force():
            #based on least square's inverse fit of the four data points in the voltage limited range
            #an invrse function fit much better than an exponential function
            a = 11106.0578548174
            b = 3.8205311947127
            if train.speed < b:
                return 10**6
            else:
                return a/(train.speed - b)
        
        def commutator_limited_force():
            #based on least square's inverse fit of the four data points in the commutator limited range
            #an invrse function fit much better than an exponential function
            a = 3278.06787794513
            b = 58.1194383702459
            if train.speed < b:
                return 10**6
            else:
                return a/(train.speed - b)
        
        
        def current_or_field_limited_force():
            #define the velocity above which the linear field limited and current limited regimes end
            #above this speed, the dynamic brakes are limited by the system's voltage or the motors' commutators
            current_limit_velocity = 51.08433735
            if train.speed < current_limit_velocity:
                for k in range(len(v_points) - 1):
                    if train.speed >= v_points[k]:
                        v1 = v_points[k]
                        v2 = v_points[k + 1]
                        F1 = F_points[k]
                        F2 = F_points[k + 1]
                        F = linear_interpolation(train.speed,v1,v2,F1,F2)
                    else:
                        break
                return F
            else:
                return 10**6


        #the dynamic braking force is limited by either the field, current, 
            #voltage, or commutator.  In practice, each of these limits will 
            #apply at different speeds, but we can take the minimum instead
            #op explicitly using the speed to determine which regime we're in
        self.dynamic_brake_force =  min(voltage_limited_force(), 
                                            commutator_limited_force(), 
                                            current_or_field_limited_force())
        
        #even after the braking force is calculated from the speed, we need to check
            # that it does not exceed the locomotives adhesion on the rails
        path.track_class(train.location)
        adhesion_limit = self.weight * 1000 * gravity * path.adhesion
        self.dynamic_brake_force = min(self.dynamic_brake_force, 
                                       adhesion_limit)


    def calculate_brake_force(self,train,path):
        self.air_brake(train,path)
        self.rheostatic_dynamic_brake(train,path)
        
        #the total braking force on the locomotive will be the combination of
            #the locomotive's air brakes and its dynamic brakes.  These must
            #still be below the locomotive's adhesion limit
        adhesion_limit = self.weight * 1000 * gravity * path.adhesion
        self.brake_force = min(self.air_brake_force + self.dynamic_brake_force,
                               adhesion_limit)

        
    
    def air_compressor(self):
        '''
        train_line_diameter = 1.25 * 2.54 #cm - assumes 1 1/4 inch diameter line, which is typical according to Hay
        train_line_length = 1.03*train.length #assume the total line length is roughly 3% higher than the train length to account for slack betwixt cars
        train_line_volume = (math.pi*(train_line_diameter/2)**2)*train_line_length
        
        brake_cylinder_diameter = 
        brake_cylinder_radius = 
        brak_cylinder_area = 
        #brake_cylinder_full_service_length = 8*2.54 #cm - double check this in Hay
        brake_cylinder_emergency_length = 
        '''
        pass
        
class diesel_electric(Locomotive):
    pass

class electric(Locomotive):
    
    def regenerative_dynamic_brake(self, train, path):
        #for electric locomotives
        #based on figure 9.31 on page 259 of Iwnicki's Handbook
        #velocity in kph, braking force in kN
        
        def linear_interpolation(x, x1, x2, y1, y2):
            m = (y2 - y1)/(x2 - x1) #slope is rise over run
            return y1 + m*(x - x1)
        
        #points of velocity vs force in the field and current limited regimes
        v_points = [0.0,
                    14.19354839,
                    50.0]
        F_points = [0.0,
                    237.2093023,
                    236.0465116]
        
        def voltage_limited_force(v):
            #based on least square's inverse fit of the four data points in the voltage limited range
            #an invrse function fit much better than an exponential function
            a = 11183.7781754323
            b = 1.84558074479204
            if v < b:
                return 10**6
            else:
                return a/(v - b)
        
        def commutator_limited_force(v):
            #based on least square's inverse fit of the four data points in the commutator limited range
            #an invrse function fit much better than an exponential function
            a = 3266.80579274212
            b = 58.6341079332544
            if v < b:
                return 10**6
            else:
                return a/(v - b)
        
        
        def current_or_field_limited_force(v):
            #define the velocity above which the linear field limited and current limited regimes end
            #above this speed, the dynamic brakes are limited by the system's voltage or the motors' commutators
            current_limit_velocity = 50.0
            if v < current_limit_velocity:
                for k in range(len(v_points) - 1):
                    if v >= v_points[k]:
                        v1 = v_points[k]
                        v2 = v_points[k + 1]
                        F1 = F_points[k]
                        F2 = F_points[k + 1]
                        F = linear_interpolation(v,v1,v2,F1,F2)
                    else:
                        break
                return F
            else:
                return 10**6
        
        self.regenerative_brake_force = min(voltage_limited_force(train.speed), 
                    commutator_limited_force(train.speed), 
                    current_or_field_limited_force(train.speed))
        
        #the regenerative brake_force can be limited by the capacity of the OCS
            #to accept power
        #in this case, we'll send the maxmimum power to the OCS, and then 
            #calculate the remaining rheostatic braking force
        
        
        if self.regenerative_brake_force * train.speed < self.return_limit:
            #the regenerative brake is producing more power than the grid can
                #accept.  The power is limited by the return
            self.power_return = self.return_limit
            self.regenerative_brake_force = self.return_limit/train.speed
            
            #techinically, if some of the power is going to the grid, the 
                #resistors would have more capacity than in a diesel-electric
                #because we should be further from heat saturation
                #For now, we'll assume that the rheostatic brakes have the same 
                #limit as in a diesel-electric
            self.rheostatic_dynamic_brake(train,path)
            self.return_limited = True
        
        else:
            self.power_return = self.regenerative_brake_force * train.speed
            self.dynamic_brake_force = self.regenerative_brake_force
            self.return_limited = False
        
    def calculate_brake_force(self,train,path):
        self.air_brake(train,path)
        self.regenerative_dynamic_brake(train,path)
        
        #the total braking force on the locomotive will be the combination of
            #the locomotive's air brakes and its dynamic brakes.  These must
            #still be below the locomotive's adhesion limit
        path.track_class(train.location)
        adhesion_limit = self.weight * 1000 * gravity * path.adhesion(train.location)
        self.brake_force = min(self.air_brake_force + self.dynamic_brake_force,
                               adhesion_limit)
            
