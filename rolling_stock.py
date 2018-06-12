#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 28 08:52:38 2018

@author: Walthall
"""
gravity = 9.81 #m/s^2
temperature = 20 #degrees Celsius
import route
import density
import os, csv
import numpy as np
import math
import matplotlib.pyplot as plt
import time as tm

start_time = tm.time()

timestep = 10.0

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
        
    def air_brake(self, train, path, service_level):
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

            return linear_interpolation(v,v1,v2,f1,f2)
        
        if train.emergency_brake:
            service_level == 1.0
        
        if service_level == 0:
            self.air_brake_force = 0
        else:
            #The friction coefficient should determine the maximum breaking potential for a full-service brake
            # we will assume that the railcar is designed to apply x% of its tare weight at maximum friction coefficient
            self.air_brake_force = (gravity * 1000 * self.tare * path.adhesion
                                    * self.brake_percent 
                                    * friction_coefficient(train.speed)
                                    /friction_coefficient(0))*service_level
        if train.emergency_brake:
            self.air_brake_force *= 1.3

    def calculate_brake_force(self,train,path):
        self.air_brake(train,path,0)
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

class Locomotive(Rolling_stock):
    
    def __init__(self, length, axles, weight, power, traction, truck_spacing):
        self.length = length
        self.axles = axles
        self.weight = weight
        self.tare = weight
        self.max_power = power
        self.power = power
        self.traction = traction
        self.truck_spacing = truck_spacing
        self.type = 'Leading Freight Locomotive'
        
        self.w = self.weight/self.axles
        
        self.gross = self.weight
        
        self.max_throttle = 8
        self.brake_percent = 0.9
    
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
    
        self.dynamic_brake_force =  min(voltage_limited_force(), 
                                            commutator_limited_force(), 
                                            current_or_field_limited_force())


    def calculate_brake_force(self,train,path):
        self.air_brake(train,path,0)
        self.rheostatic_dynamic_brake(train,path)
        
        self.brake_force = self.air_brake_force + self.dynamic_brake_force
        
        

        
    
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
    
    def regenerative_dynamic_brake(self, train):
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
        
        self.power_return = self.regenerative_brake_force * train.speed

    
    
    
    





def build_unit_train(number_of_cars,tonnage_per_car, tare_weight, ruling_grade,
                     loco_power, loco_traction,des_speed,C,a):
    
    #calculate number of locomotives
    total_mass = number_of_cars * (tonnage_per_car + tare_weight)
    car_weight = tare_weight + tonnage_per_car
    
    #the number of locomotives is determined by either the ruling grade or the
    #desired speed
    
    #if ruling grade is the limiting factor, we care about the maximum tractive
    #effort
    grade_resistance = total_mass * gravity * ruling_grade * 1000
    #for now, assume four axles per car
    crawl_speed = 10 #mph
    w = car_weight/1.1 / 4 #weight per axle in tons
    R = (1.5 + 18/w + 0.03*crawl_speed*2.23694 + C*a*((crawl_speed*2.23694)**2)
        /10000/(car_weight/1.1))
    number_of_locomotives_grade = int((grade_resistance + R*(total_mass/1.1)*4.44822) / 
                                loco_traction) + 1
    
    
    #if the desired speed (on flat level terrain) is the limiting factor, we care
    #about maximum power on flat level track
    R = (1.5 + 18/w + 0.03*des_speed*2.23694 + C*a*((des_speed*2.23694)**2)
        /10000/(car_weight/1.1))
    tractive_effort = R*(total_mass/1.1)*4.44822 #in Newtons
    Power = tractive_effort * des_speed
    number_of_locomotives_speed = int(Power/loco_power) + 1
    
    number_of_locomotives = max(number_of_locomotives_grade, 
                                number_of_locomotives_speed)
    
    '''
    To do:
    calculate the drawbar pull and see if any of the locomotives need to be placed
    at the rear or middle
    '''
    
    front = [Locomotive(20,6,100,2984*1000,0.40,15) for k in range(number_of_locomotives)]
    cars = [Railcar('Intermodal double-stack',15,4,28.65,20.12) for k in range(number_of_cars)]
    
    #load the railcars
    for k in cars:
        k.loading(tonnage_per_car)
    
    return front + cars


loco_power = 2984*1000
max_tractive_effort = 423*1000*4.44822*0.40
#train = build_unit_train(100,100,30,0.02,loco_power,max_tractive_effort,25,5,125)

class Train(object):
    def __init__(self):
        self.consist = build_unit_train(100,100,30,0.02,loco_power,
                                        max_tractive_effort,25,5,125)
        #create separate lists for the locomotives and the railcars
        self.locomotives = [k for k in self.consist if isinstance(k, Locomotive)]
        self.loco_count = len(self.locomotives)
        self.cars = [k for k in self.consist if isinstance(k, Railcar)]
        self.car_count = len(self.cars)
        
        #calculate the train's total length
        self.length = sum([k.length for k in self.consist])
        #the train will start from rest
        #speed should always be in m/s
        self.speed = 0
        self.emergency_brake = False
        #the train will start on the route with the rear at the location 0
        self.location = self.length
        
        self.mass = sum([k.gross for k in self.consist])
        
        self.head_end_power = 0
        
        #initialise the position, location, and resistance of each element
        for k in range(len(self.consist)):
            self.consist[k].position(k)
            self.consist[k].calculate_location(self,path)
            self.consist[k].initialise_resistances(self,path)
            self.head_end_power += self.consist[k].HEP
        
        #before the train starts, it has not exceeded its maximum tractive effort
        self.max_traction_exceded = False
        self.maximum_tractive_effort = self.loco_count * max_tractive_effort
        self.calculate_total_resistance()
        self.calculate_power()
        self.calculate_total_brake_force()
        self.calculate_acceleration()
        
    
    def calculate_total_resistance(self):
        self.total_resistance = 0
        for k in self.consist:
            #add the resistance of each component
            self.total_resistance += k.R
        self.fraction_tractive_effort = (self.total_resistance
                                         /self.maximum_tractive_effort)
        #check if the total resistance is too high for the maximum tractive effort
        if self.fraction_tractive_effort > 1:
            self.max_traction_exceeded = True
    
    def calculate_power(self):
        self.power = sum([locomotive.power for locomotive in self.locomotives])
    
    def calculate_total_brake_force(self):
        self.brake_force = 0
        for k in range(len(self.consist)):
            self.consist[k].calculate_brake_force(self,path)
            self.brake_force += self.consist[k].brake_force
    
    def calculate_acceleration(self):
        if self.speed > 0:
            available_traction = min(self.maximum_tractive_effort, 
                                     (self.power - self.head_end_power)
                                      /self.speed)
        else:
            available_traction = self.maximum_tractive_effort
        
        self.acceleration = (available_traction 
                             - self.total_resistance 
                             - self.brake_force)/(self.mass*1000)
    
    def update(self):
        self.speed += self.acceleration * timestep
        self.location += (self.speed*timestep 
                          + 0.5*self.acceleration*timestep**2)
        
        #update the location and resistance of each car
        for k in range(len(self.consist)):
            self.consist[k].calculate_location(self,path)
            if self.acceleration == 0:
                self.consist[k].update_resistance_for_location(self, path)
            else:
                self.consist[k].update_resistance(self, path)
        self.calculate_total_resistance()
        self.calculate_power()
        self.calculate_acceleration()

        

path = route.Route(100000)
train = Train()


time = 0
times = [time]

velocities = [train.speed]
accelerations = [train.acceleration]
locations = [train.location]


while train.location < (100000 - 100):
    
    train.update()
    
    time += timestep
    times.append(time)
    
    velocities.append(train.speed)
    accelerations.append(train.acceleration)
    locations.append(train.location)

print(train.location)
print(train.speed)
print(time)

times = np.array(times)
velocities = np.array(velocities)
accelerations = np.array(accelerations)
locations = np.array(locations)

speed_at_xkm = True
for k in range(velocities.shape[0]):
#    if speed_at_xkm:
#        if locations[k] > 4*1000:
#            print(str(round(velocities[k]/train.speed*100,0)) + "%")
#            speed_at_xkm = False
    if velocities[k] > 0.50*train.speed:
        print(str(times[k]/60) + " minutes")
        print(str(round(locations[k]/1000,1)) + " km")
        print(velocities[k])
        print(k)
        break


fig = plt.figure()
fig.suptitle("Train acceleration distance")
ax1 = fig.add_subplot(211)
ax1.plot(times/60, velocities)
plt.ylabel("speed, (m/s)")

ax1.annotate('50% max speed\nafter two minutes',
            xy=(2, velocities[12]), xycoords='data',
            xytext=(100, -30), textcoords='offset points',
            arrowprops=dict(arrowstyle="->",
                            connectionstyle="arc3,rad=-.1"))

ax1.annotate('90% max speed\nafter 10.5 minutes',
            xy=(10.5, velocities[63]), xycoords='data',
            xytext=(100, -30), textcoords='offset points',
            arrowprops=dict(arrowstyle="->",
                            connectionstyle="arc3,rad=-.1"))

ax2 = fig.add_subplot(212)
ax2.plot(times/60, locations/1000)
plt.ylabel("distance traveled (km)")
plt.xlabel("time, (minutes)")

for ax in [ax1, ax2]:
    ax.axvline(x = 2.0,  c = "black", linewidth = 0.5, linestyle = "dashed")
    ax.axvline(x = 10.5, c = "black", linewidth = 0.5, linestyle = "dashed")

plt.savefig("unit intermodal train acceleration profile",dpi = 330)
plt.show()





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