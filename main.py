# -*- coding: utf-8 -*-
"""
Created on Sun Feb 18 17:22:30 2024

@author: karl_
"""

import pandas as pd
import numpy as np

from Instruments import Bond, Portfolio
import Util
from Calculator import Calculator



def main():
    
    global rates_scenario,portfolio
    global yield_change
    global fullreval_var_01, fullreval_var_05, sensi_var_01,sensi_var_05
    global dv01
    
    val_date = '2024-02-12'
    
    bond1 = Bond(cusip='CUSIP1', coupon=0.04, frequency=2, issue='2024-02-15', maturity='2026-02-15')
    bond2 = Bond(cusip='CUSIP2', coupon=0.0425, frequency=1, issue='2024-02-15', maturity='2034-02-15')
    bond3 = Bond(cusip='CUSIP3', coupon=0.05, frequency=2, issue='2020-01-01', maturity='2027-01-01')
    bond4 = Bond(cusip='CUSIP4', coupon=0.03, frequency=1, issue='2021-02-15', maturity='2051-02-15')

## construct bond portoflio    
    instruments = [bond1, bond2, bond3, bond4]
    
    ## check bond attributes is valid 
    for i in instruments:
        i.validate_bond(val_date)
    
    p = Portfolio([bond1,bond2,bond3,bond4])
    
    p.generate_random_weight()
##  assignment 5: uncomment below line to manually input bond weights such as 0.25,0.25,0.25,0.25
##  p.user_input_weights()
    
    portfolio = p.portfolio
    portfolio.to_csv("portfolio.csv", index=False)

## construct Calculator for risk calculation purpose    
    calculator = Calculator()
    ## assignment 1: below is how to use sql query to obtain data from database
    rates_scenario = calculator.get_historical_rates_scenario()
    
    ## assignment 2: calculate portfolio yield change. Method: calculate each bond's daily yield change and aggregate to portfolio level for the past two years 
    yield_change = calculator.calculate_yield_change(portfolio, val_date)
    yield_change.to_csv("yield_change.csv", index=True)
    
    ## assignment 3: historical simulation (full-reval) VaR: price each bond's price using historical rates scenario, and aggregate to portfolio value, then calculate pnl and take 1% and 5% percentile value 
    fullreval_var_01 = calculator.calculate_portfolio_var(portfolio, val_date, 0.01)
    fullreval_var_05 = calculator.calculate_portfolio_var(portfolio, val_date, 0.05)
    
    print('Full Revaluation Approach -----')
    print(f'The portfolio is valued as of {val_date} using the data from 2022-02-11 to 2024-02-12')
    print(f'1-day Value at Risk (VaR) at 99% confidence level: {fullreval_var_01:.4f}')
    print(f'1-day Value at Risk (VaR) at 95% confidence level: {fullreval_var_05:.4f}')
    
    ## assignment 4: bump the historical scenario up and down, re-price the bonds, and calculate dv01 and -(pv_up - pv_down)/(2*bump size in bps)
    dv01 = calculator.calculate_dv01(portfolio, val_date, 5)
    dv01.to_csv("dv01.csv", index=False)
    
    ## assignment 5: sensitivity-based historical simulation VaR approach. use the dv01 as of the valuation date and multiply the historical yield rate change to calculate pnl, and then take 1% and 5% percentile value
    sensi_var_01 = calculator.calculate_portfolio_sensitivity_based_var(portfolio, dv01, val_date, 0.01)
    sensi_var_05 = calculator.calculate_portfolio_sensitivity_based_var(portfolio, dv01, val_date, 0.05)
    print('Sensitivity based Approach -----')
    print(f'The portfolio is valued as of {val_date} using the data from 2022-02-11 to 2024-02-12')
    print(f'1-day Value at Risk (VaR) at 99% confidence level: {sensi_var_01:.4f}')
    print(f'1-day Value at Risk (VaR) at 95% confidence level: {sensi_var_05:.4f}')

if __name__ == "__main__":
    main()