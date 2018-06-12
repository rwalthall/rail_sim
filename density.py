#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 25 11:52:58 2018

@author: Walthall
"""

#calculate the air pressure given a specific altitude and temperature
#height, h, given in metres above sea-level
#temperature, T, given in degrees Celsius
def pressure(h, T):
    #pressure at sea level, in Pascals
    P_0 = 100325 #Pa
    #temperature lapse rate, in Kelvin per metre
    L = 0.0065 #K/m
    #reference temperature in Kelvin
    T_0 = T + 273.15
    #gravitational acceleration, in metres per second squared
    g = 9.80665 #m/s^2
    #Molar mass of dry air
    M = 0.0289644 #kg/mol
    #universal gas constant in SI units
    R_0 = 8.31447 #J/(mol∙K)
    
    P = P_0*(1 - (L*h)/T_0)**((g*M)/(R_0*L))
    return P

#calculate the air density given the pressure and temperature
#pressure, P, given in Pascals
#temperature, T, given in degrees Celsius
def density_P(P, T):
    #convert the temperature to Kelvin
    T_0 = T + 273.15
    #Molar mass of dry air
    M = 0.0289644 #kg/mol
    #universal gas constant in SI units
    R_0 = 8.31447 #J/(mol∙K)
    
    rho = P*M/(R_0*T_0)
    return rho

#calculate the air density for a given height
#height, h, given in metres above sea-level
#temperature, T, given in degrees Celsius
def density_h(h, T):
    rho = density_P(pressure(h,T),T)
    return rho
    

    