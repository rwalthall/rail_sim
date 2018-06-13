#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 12 11:02:18 2018

@author: Walthall
"""

from railcar import Railcar
from locomotives import Locomotive
import route
from constants import gravity, timestep
import constants

import matplotlib.pyplot as plt
import numpy as np

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
    number_of_locomotives_grade = int((grade_resistance 
                                       + R*(total_mass/1.1)*4.44822)
                                       / loco_traction) + 1
    
    
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
    
    front = [Locomotive(20,6,100,loco_power,loco_traction,15) for k in range(number_of_locomotives)]
    cars = [Railcar('Intermodal double-stack',15,4,28.65,20.12) for k in range(number_of_cars)]
    
    #load the railcars
    for k in cars:
        k.loading(tonnage_per_car)
    
    return front + cars


loco_power = 2984*1000 #W, based on 4000 HP
max_tractive_effort = 423*1000*4.44822*0.40 #N
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
        self.speed_limit_exceded = False
        #start with both the dynamic and air brakes off
        self.dynamic_brake = 0
        #the air brake system's state is described by the service level
            #applying a full service brake from the air brakes would here be 
            #represented by setting the service level to 1.0
        self.service_level = 0
        #emergency brakes can be applied to apply a force beyond the full 
            #service level through the air brake system
        self.emergency_brake = False
        #the train will start on the route with the rear at the location 0
        self.location = self.length
        
        self.mass = sum([k.gross for k in self.consist])
        
        
        '''
        create a routine to calculate the HEP
        '''
        self.head_end_power = 0
        
        #determine the train's power for each throttle notch
        #set the train's number of notches to the minimum number for all of its
            #locomotives
            
        '''
        for now, we'll only handle the case where all locomotives have the same
        number of throttle notches
        '''
        self.throttle = 0
        self.max_throttle = self.locomotives[0].max_throttle
        self.max_power = 0.0
        self.power = 0.0
        for k in range(len(self.locomotives)):
            if self.locomotives[k].max_throttle < self.max_throttle:
                self.max_throttle = self.locomotives[k].max_throttle
            self.max_power += self.locomotives[k].max_power
            self.power += self.locomotives[k].power
        self.power_by_throttle = {}
        for k in range(self.max_throttle + 1):
            self.power_by_throttle[k] = self.max_power * (k/self.max_throttle)**2
        
        
        
        #initialise the position, location, and resistance of each element
        for k in range(len(self.consist)):
            self.consist[k].position(k)
            self.consist[k].calculate_location(self,path)
            self.consist[k].initialise_resistances(self,path)
            self.head_end_power += self.consist[k].HEP
        
        #before the train starts, it has not exceeded its maximum tractive effort
        self.max_traction_exceded = False
        self.maximum_tractive_effort = 0
        for k in range(len(self.locomotives)):
            self.maximum_tractive_effort += self.locomotives[k].maximum_tractive_effort
        
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
        for component in self.consist:
            component.calculate_brake_force(self, path)
            
            self.brake_force += component.brake_force
    
    def calculate_acceleration(self):
        if self.speed > 0:
            available_traction = min(self.maximum_tractive_effort, 
                                     (self.power - self.head_end_power)
                                      /self.speed)
        else:
            available_traction = self.maximum_tractive_effort
        
        
        #other than wind and grade resistances, the resistive forces only act to
            #resist motion
        '''
        separate out the resistive forces that can act when the train is at rest
        such as grade resistance
        '''
        resistance = self.total_resistance + self.brake_force
        
        if resistance > available_traction:
            if self.power == 0:
                resistance = available_traction
        
        #Thank you, Isaac
        self.acceleration = (available_traction - resistance)/(self.mass*1000)
        
        
        
    def calculate_throttle(self, path):
        #three cases:
            #1)current speed is below the speed limit
            #2)current speed is at the speed limit, but a lower speed limit is
                #approaching
            #3)current speed is at the speed limit, and there is no change ahead
        
        path.current_speed_limit(self.location)
        speed_limit = path.speed_limit
        desired_speed = path.speed_limit
        
        if (path.determine_speed_limit(self.location + constants.lookahead) 
        < desired_speed):
            desired_speed = (path.determine_speed_limit(self.location 
                                                        + constants.lookahead))
        
        #check if the train has passed the speed limit for the route
        if self.speed > speed_limit:
            self.speed_limit_exceded = True
        
        
        
        #set a threshold below the desired speed within which we don't care about
            #accelerating the train further
        upper_threshold = constants.upper_threshold
        lower_threshold = constants.lower_threshold
        
        throttle_changed = False
        
        if self.speed < desired_speed - lower_threshold:
            #advance the throttle one notch if possible
            if self.throttle < self.max_throttle:
                self.throttle += 1
                throttle_changed = True
        if self.speed > desired_speed - upper_threshold:
            #lower the throttle one notch if possible
            if self.throttle > 0:
                self.throttle -= 1
                throttle_changed = True
        
        if throttle_changed:
            #set the throttle in each locomotive to the new position
            for locomotive in self.locomotives:
                #this locomotive method automatically recalculates the locomotive's
                    #new power
                locomotive.throttle(self.throttle)
            #recalculate the total power for the train
            self.calculate_power()

    def calculate_brake_application(self, path):
        '''
        
        using a different method from the following for now
        
        #determine what the train's likely speed would be at 0 throttle after
        #three km (the lookahead distance defined in constants.py), 
        #and decide if that puts us over the speed limit
        #for now, we'll assume constant acceleration
        
        acceleration_without_power = -self.total_resistance/(self.mass*1000)
        potential_speed = ((2*acceleration_without_power*constants.lookahead) 
                           + self.speed**2)**0.5
        '''
        desired_speed = min(path.determine_speed_limit(self.location 
                                                   + constants.lookahead),
                            path.determine_speed_limit(self.location))
        
        #determine the additional brake force necessary to reach the desired 
        #speed in the required distance
        needed_brake_force = ((self.mass*1000*(self.speed**2 - desired_speed**2)
                              /(2*constants.lookahead)) 
                              - self.total_resistance - self.brake_force)
        
        #if the needed_brake_force is positive, we need to apply some brakes:
        if needed_brake_force > 0:
            #first increase the dynamic brake if possible:
            if self.dynamic_brake < 1.0:
                self.dynamic_brake += constants.dynamic_brake_increment
            #if the dynamic brake is already saturated, resort to the air brake system:
            elif self.service_level < 1.0:
                self.service_level += constants.air_brake_increment
        #if the needed_brake_force is negative, we need to release some brakes:
        else:
            #release the air brake first:
            if self.service_level > 0:
                self.service_level -= constants.air_brake_increment
            elif self.dynamic_brake > 0:
                self.dynamic_brake -= constants.dynamic_brake_increment
        


            
        
    
    def apply_air_brake(self, path):
        for k in range(len(self.consist)):
            self.consist[k].air_brake(self, path)
    
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

        self.calculate_throttle(path)
        self.calculate_brake_application(path)     
        self.calculate_total_brake_force()
        
        self.calculate_total_resistance()
        self.calculate_power()
        self.calculate_acceleration()

path = route.Route(100000)
train = Train()


time = 0
times = [time]


#train.speed = 0

velocities = [train.speed]
accelerations = [train.acceleration]
locations = [train.location]
elevations = [path.elevation(train.location)]


while train.location < (100000 - 100):
    
    train.update()
    
    time += timestep
    times.append(time)
    
    velocities.append(train.speed)
    accelerations.append(train.acceleration)
    locations.append(train.location)
    elevations.append(path.elevation(train.location))

print(train.location)
print(train.speed)
print(time)

times = np.array(times)
velocities = np.array(velocities)
accelerations = np.array(accelerations)
locations = np.array(locations)
elevations = np.array(elevations)

#speed_at_xkm = True
#for k in range(velocities.shape[0]):
##    if speed_at_xkm:
##        if locations[k] > 4*1000:
##            print(str(round(velocities[k]/train.speed*100,0)) + "%")
##            speed_at_xkm = False
#    if velocities[k] > 0.50*train.speed:
#        print(str(times[k]/60) + " minutes")
#        print(str(round(locations[k]/1000,1)) + " km")
#        print(velocities[k])
#        print(k)
#        break


fig = plt.figure()
fig.suptitle("Train acceleration distance")
ax1 = fig.add_subplot(211)
ax1.plot(times/60, velocities)
plt.ylabel("speed, (m/s)")

#ax1.annotate('50% max speed\nafter two minutes',
#            xy=(2, velocities[12]), xycoords='data',
#            xytext=(100, -30), textcoords='offset points',
#            arrowprops=dict(arrowstyle="->",
#                            connectionstyle="arc3,rad=-.1"))
#
#ax1.annotate('90% max speed\nafter 10.5 minutes',
#            xy=(10.5, velocities[63]), xycoords='data',
#            xytext=(100, -30), textcoords='offset points',
#            arrowprops=dict(arrowstyle="->",
#                            connectionstyle="arc3,rad=-.1"))

ax2 = fig.add_subplot(212)
ax2.plot(times/60, locations/1000)
plt.ylabel("distance traveled (km)")
plt.xlabel("time, (minutes)")

for ax in [ax1, ax2]:
    ax.axvline(x = 2.0,  c = "black", linewidth = 0.5, linestyle = "dashed")
    ax.axvline(x = 10.5, c = "black", linewidth = 0.5, linestyle = "dashed")

plt.savefig("unit intermodal train acceleration profile",dpi = 330)
plt.show()



