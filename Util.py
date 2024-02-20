# -*- coding: utf-8 -*-
"""
Created on Thu Feb 15 23:28:38 2024

@author: karl_
"""

import sqlite3
import pandas as pd
import numpy as np

## Use sqlite to retrieve data from YieldData.db
def RetrieveYields(instruments: list[str] = ['ALL'], start_date:str = '2022-02-11', end_date: str = '2024-02-12'):

## by default, all tenor points over the past two years should be retrieved    
    if instruments == ['ALL']:
        query = f"SELECT DATE, name, yield_rate FROM YieldData WHERE DATE BETWEEN '{start_date}' AND '{end_date}' ORDER BY DATE"
    else:
        instruments = ",".join([f"'{instrument}'" for instrument in instruments])
        query = f"SELECT DATE, name, yield_rate FROM YieldData WHERE DATE BETWEEN '{start_date}' AND '{end_date}' AND name IN ({instruments}) ORDER BY DATE"
    
    con = sqlite3.connect('YieldData.db')
    cur = con.cursor()
    
    res = cur.execute(query)
    data = res.fetchall()

## convert the retrieved data to dataframe    
    df = pd.DataFrame(data, columns=[col[0] for col in cur.description])
    
    cur.close()
    con.close()
    
    return df

## This is helper function to generate n random numbers sum up to 1. 
def generate_random_weights(n):
    random_numbers = np.random.rand(n)
    random_numbers = random_numbers/np.sum(random_numbers)
    return random_numbers

## This is a validator function to check if all needed treasury yield tenor points are loaded.
def validate_rates_availability(cusip_to_yield:pd.DataFrame, rates: pd.DataFrame):
    name1 = cusip_to_yield['name'].unique()
    name2 = rates['name'].unique()
## For example, if we have a 30-year bond, but rates do not include 'TRY30', then the missing_name is non-empty
    missing_name = set(name1) - set(name2)
    if missing_name:
        raise ValueError(f'Rates {missing_name} are missing.')


## This is to project bond cashflow given the bond attributes
def project_cashflow(bond:dict):
    bond['issue'] = pd.to_datetime(bond['issue'], format=('%Y-%m-%d'))
    bond['maturity'] = pd.to_datetime(bond['maturity'],format=('%Y-%m-%d'))
    
## interval is the time period between two payments. frequency 2 means semi-annual pay, 4 means quarterly pay, etc. 0 means no coupon payment.   
    if bond['frequency']!=0:
        interval = 12/bond['frequency']
    else:
        interval = 9999
    
    cash_flow = []

## generate a list of pairs including payment date and payment amount, and return.    
    if interval !=9999:
        next_payment_date = bond['issue'] 
        while next_payment_date < bond['maturity']:
            next_payment_date = pd.to_datetime(next_payment_date + pd.DateOffset(months=interval),format=('%Y-%m-%d'))
            payment = bond['coupon']/bond['frequency']
            if next_payment_date == bond['maturity']: payment += 1.0
            cash_flow.append((next_payment_date,payment))
    else:
        cash_flow.append((bond['maturity'],1.0))
            
    return cash_flow

## based on bond's maturity date and valuation date, map it to the nearest yield curve tenor points. This is bucketing method.
def get_yieldcurve_tenor_name(bond:dict, valuation_date:pd.Timestamp):
    end_date = pd.to_datetime(bond['maturity'],format=('%Y-%m-%d'))
    val_date = pd.to_datetime(valuation_date,format=('%Y-%m-%d'))
    years_to_maturity = (end_date - val_date).days / 365.25

    if years_to_maturity <= 0.75:
        tenor_name = 'TRY3MO'
    elif years_to_maturity < 1.5:
        tenor_name = 'TRY1'
    elif years_to_maturity < 2.5:
        tenor_name = 'TRY2'
    elif years_to_maturity < 4:
        tenor_name = 'TRY3'
    elif years_to_maturity < 7.5:
        tenor_name = 'TRY5'
    elif years_to_maturity < 15:
        tenor_name = 'TRY10'
    elif years_to_maturity < 25:
        tenor_name = 'TRY20'
    else:
        tenor_name = 'TRY30'
    
    return tenor_name


## this is the key pricing function. It takes the cash flow, and generate PV by discounting each payment given the rates based on the time between valuation date and payment date. 
def calculate_discounted_cashflow_pv(valuation_date, cash_flow, scenario):

    scenario = float(scenario)/100.0
    pv = 0

    for date, amount in cash_flow:
        time_to_payment = (date - pd.to_datetime(valuation_date)).days / 365.25  
        discount_factor = np.exp(-scenario * time_to_payment)  
        discounted_amount = amount * discount_factor 
        pv += discounted_amount 
    
    return pv


            
            
            
            
            
            
            
            
            
            
            
            