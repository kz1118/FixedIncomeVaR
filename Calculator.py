# -*- coding: utf-8 -*-
"""
Created on Fri Feb 16 19:02:58 2024

@author: karl_
"""

import numpy as np
import pandas as pd


import Util
import Instruments


class Calculator():
    def __init__(self):
        pass

## Retrieves historical yield rates within a specified time frame and return a dataframe    
    def get_historical_rates_scenario(self, yields: list[str] = ['ALL'], start_date:str = '2022-02-11', end_date: str = '2024-02-12'):
        rates = Util.RetrieveYields(yields, start_date, end_date)
        rates['yield_rate'] = rates['yield_rate'].astype(float)
        return rates

## Maps each bond in the portfolio to a corresponding yield curve tenor based on its maturity.    
    def map_positions_to_yieldcurve(self, portfolio:pd.DataFrame, valuation_date:pd.Timestamp):
        for index, row in portfolio.iterrows():
            row_dict = row.to_dict()
            portfolio.loc[index,'name']= Util.get_yieldcurve_tenor_name(row_dict,valuation_date)
        return portfolio

## Calculates the change in yield rates for each bond in the portfolio    
    def calculate_yield_change(self, portfolio:pd.DataFrame,valuation_date:pd.Timestamp):
        rates = self.get_historical_rates_scenario()
        ## calculate historical treasury yield rates daily change
        rates['rate_diff'] = rates['yield_rate'] - rates.groupby('name')['yield_rate'].shift(1)
        rates.dropna(inplace=True)
        
        portfolio = self.map_positions_to_yieldcurve(portfolio, valuation_date)
        ## for each position, calculate weighted yield change. If the yield change is disired at position level, return this table.        
        daily_weighted_yield_diff = pd.merge(rates, portfolio[['name','cusip','weight']], on=['name'], how = 'left').assign(weighted_yield_diff=lambda x: x['rate_diff']*x['weight'])
        ## aggregate position yield change to portfolio level.
        daily_total_diff = daily_weighted_yield_diff[['DATE','weighted_yield_diff']].groupby('DATE').sum() 
        return daily_total_diff

##  Calculates the prices of bonds in the portfolio based on yield rates        
    def calculate_price(self, portfolio:pd.DataFrame, valuation_date:pd.Timestamp, rates:pd.DataFrame):
        cash_flow = {}
        portfolio = self.map_positions_to_yieldcurve(portfolio, valuation_date)
        ## make sure there are some positions in the portfolio
        if portfolio.shape[0]==0:
            raise ValueError('The portfolio is empty')
        for index, row in portfolio.iterrows():
            row_dict = row.to_dict()
            cash_flow[row_dict['cusip']] = Util.project_cashflow(row_dict)
        
        cusip_to_yield = portfolio.set_index('cusip')['name'].to_dict()
        
        ## check all bonds' corresponding tenor points data exist
        Util.validate_rates_availability(portfolio, rates)
        
        price_table  = pd.DataFrame([(date, cusip) for date in rates['DATE'].unique() for cusip in portfolio['cusip']], columns=['DATE', 'cusip'])
        ## this is Key calculation method. Pass valuation date, cash flow, and historical rates scenario to the discount cash flow PV calculator. 
        price_table['price'] = price_table.apply(lambda x: Util.calculate_discounted_cashflow_pv(valuation_date,cash_flow[x['cusip']],rates.loc[(rates['DATE']==x['DATE']) & (rates['name']==cusip_to_yield[x['cusip']]),'yield_rate'].values[0]), axis=1)
        ## the return table is the price of each cusip over the last two years.
        return price_table
    
## Calculates the total value of the portfolio based on bond prices and weights    
    def calculate_portfolio_value(self, portfolio:pd.DataFrame, valuation_date:pd.Timestamp):
        rates = self.get_historical_rates_scenario()
        price_table = self.calculate_price(portfolio, valuation_date, rates)
        ## multiply price and weights for each instrument to get the portfolio value over the past two years
        value = pd.merge(price_table, portfolio[['cusip','weight']], on=['cusip'], how = 'left').assign(weighted_value=lambda x: x['price']*x['weight'])
        total_value = value[['DATE','weighted_value']].groupby('DATE').sum()
        return total_value

## Calculates the Value at Risk (VaR) for the portfolio based on a specified threshold    
    def calculate_portfolio_var(self, portfolio:pd.DataFrame, valuation_date:pd.Timestamp, threshold):
        total_value = self.calculate_portfolio_value(portfolio, valuation_date)
        ## calculate daily value change, and use quantile method to return the 1% and 5% percentile value.
        daily_diff = total_value.diff().fillna(0)  
        var = (-1.0)*daily_diff.quantile(threshold)
        return var[0]

## Calculates the Dollar Value of a 01 (DV01) for each bond in the portfolio    
    def calculate_dv01(self, portfolio:pd.DataFrame, valuation_date:pd.Timestamp, bump_size_in_bp:int):
        rates = self.get_historical_rates_scenario()
        rates_up, rates_down = rates.copy(), rates.copy()
        ## generate rates_up scenario and rates_down scenario by parallel shifting the historical curves with certain size 
        rates_up['yield_rate'] = rates_up['yield_rate'] + bump_size_in_bp/100.0
        rates_down['yield_rate'] = rates_down['yield_rate'] - bump_size_in_bp/100.0
        ## produce the price of instruments under these two scenario
        price_up_table = self.calculate_price(portfolio, valuation_date, rates_up)
        price_down_table = self.calculate_price(portfolio, valuation_date, rates_down)
        ## calculate dv01 as -(pv_up -pv_down)/(2*bump_size_in_bp)
        price_up_table['price_diff'] = price_down_table['price']-price_up_table['price']
        dv01_table = price_up_table[['DATE','cusip','price_diff']].assign(dv01=lambda x: x['price_diff']/(2*bump_size_in_bp))
        return dv01_table[['DATE','cusip','dv01']]

## Calculates the VaR for the portfolio based on the sensitivity of each bond's DV01 to yield curve changes    
    def calculate_portfolio_sensitivity_based_var(self, portfolio:pd.DataFrame, dv01:pd.DataFrame, valuation_date:pd.Timestamp, threshold):
        ## only the dv01 on valuation date is needed
        dv01_val_date = dv01.loc[dv01['DATE']==valuation_date,]
        portfolio = self.map_positions_to_yieldcurve(portfolio, valuation_date)
        ## calculate treasury yield tenor points level dv01
        weighted_dv01_val_date = pd.merge(dv01_val_date, portfolio[['cusip','weight','name']], on=['cusip'], how = 'inner').assign(weighted_dv01=lambda x: x['dv01']*x['weight'])
        weighted_dv01_val_date = weighted_dv01_val_date[['name','weighted_dv01']].groupby('name').sum()
        rates = self.get_historical_rates_scenario()
        rates['rate_diff'] = (rates['yield_rate'] - rates.groupby('name')['yield_rate'].shift(1))*100
        rates.dropna(inplace=True)
        ## calculate sensitivity based pnl as valudation date's dv01 multiple yield rate change over past two years per tenor point
        sensi_pnl = pd.merge(rates, weighted_dv01_val_date, on=['name'], how = 'left').assign(pnl=lambda x: x['rate_diff']*x['weighted_dv01'])
        sensi_total_pnl = sensi_pnl[['DATE','pnl']].groupby('DATE').sum()
        ## calculate VaR as 1% and 5% percentile value
        var = (-1.0)*sensi_total_pnl.quantile(threshold)
        return var[0]
        


