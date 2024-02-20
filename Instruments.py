# -*- coding: utf-8 -*-
"""
Created on Fri Feb 16 16:46:12 2024

@author: karl_
"""


import pandas as pd
import numpy as np

import Util

## Bond class defines bond object with all required attributes.
class Bond():
    def __init__(self, cusip,coupon, frequency, issue, maturity):
        self.cusip = cusip
        self.coupon = coupon
        self.frequency = frequency
        self.issue = issue
        self.maturity = maturity
    
    def get_bond_info(self):
        return {'cusip':self.cusip,'issue':self.issue,'maturity':self.maturity,'coupon':self.coupon, 'frequency':self.frequency }

## check the desired values are correctly input before construct the portfolio    
    def validate_bond(self, val_date: pd.Timestamp):
        if self.frequency not in [1,2,4,12]:
                raise ValueError(f"CUSIP {self.cusip} error: The frequency of a bond must be in 1, 2, 4, 12")
        if self.maturity < val_date:
                raise ValueError(f' CUSIP {self.cusip} error: The bond maturity date must be after the valuation date')

## the Portfolio class consist of a list of bonds
class Portfolio():
    def __init__(self, bonds:list[Bond]):
        self.portfolio = pd.DataFrame([bond.get_bond_info() for bond in bonds])
        self.portfolio['issue'] = pd.to_datetime(self.portfolio['issue']).dt.strftime('%Y-%m-%d')
        self.portfolio['maturity'] = pd.to_datetime(self.portfolio['maturity']).dt.strftime('%Y-%m-%d')

## user can switch between generate random weights using generate_random_weight or manually input weights using user_input_weights    
    def generate_random_weight(self):
        self.portfolio['weight'] = Util.generate_random_weights(self.portfolio.shape[0])
        
    def user_input_weights(self):
        count = self.portfolio.shape[0]
        input_string = input(f"Enter {count} values separated by commas as the weights: ")
        value_list = input_string.split(',')
        value_list = [float(value) for value in value_list] 
        if len(value_list) != count:
            raise ValueError("Please provide correct number of weights")
        value_list = value_list/np.sum(value_list)
        self.portfolio['weight'] = value_list

    
        
        