# -*- coding: UTF-8 -*-

import numpy as np
import pandas as pd
from scipy.optimize import minimize
# import matplotlib.pyplot as plt


def get_smart_weight(returnDf, method='mean var', wts_adjusted=False):
    '''
    功能：输入协方差矩阵，得到不同优化方法下的权重配置
    输入：
        cov_mat  pd.DataFrame,协方差矩阵，index和column均为资产名称
        method  优化方法，可选的有min variance、risk parity、max diversification、equal weight
    输出：
        pd.Series  index为资产名，values为weight
    PS:
        依赖scipy package
    '''
    cov_mat = returnDf.cov()
    if not isinstance(cov_mat, pd.DataFrame):
        raise ValueError('cov_mat should be pandas DataFrame！')

    omega = np.matrix(cov_mat.values)  # 协方差矩阵
    def MaxDrawdown(return_list):
        '''最大回撤率'''
        return_list = (return_list+1).cumprod()
        return_list = return_list.values
        i = np.argmax(np.maximum.accumulate(return_list) - return_list)
        if i == 0:
            return 0
        j = np.argmax(return_list[:i])
        result = (return_list[j] - return_list[i]) / return_list[j]
        return result

    assetVar = returnDf.var().max()*250*0.4         #用户可承担的风险组合站所有资产最大的百分比
    assetMaxDown = returnDf.dropna().apply(MaxDrawdown).max()*0.3  #用户可承担的最大回撤组合站所有资产最大的百分比


    # 定义目标函数
    def fun1(x):  # 组合总风险
        result = np.matrix(x) * omega * np.matrix(x).T
        return result

    def fun2(x):
        tmp = (omega * np.matrix(x).T).A1
        risk = x * tmp
        delta_risk = [sum((i - risk) ** 2) for i in risk]
        return sum(delta_risk)

    def fun3(x):
        den = x * omega.diagonal().T
        num = np.sqrt(np.matrix(x) * omega * np.matrix(x).T)
        return num / den

    def fun4(x):
        port_returns = np.sum(returnDf.mean() * x) * 252
        port_variance = np.sqrt(252 * np.matrix(x) * omega * np.matrix(x).T)
        return -port_returns / port_variance

    def fun5(x):
        port_returns = -np.sum(returnDf.mean() * x) * 252
        return port_returns

    # 初始值 + 约束条件
    x0 = np.ones(omega.shape[0]) / omega.shape[0]
    bnds = tuple((0, 1) for x in x0)
    cons = ({'type': 'eq', 'fun': lambda x: sum(x) - 1})
    options = {'disp': False, 'maxiter': 1000, 'ftol': 1e-25,}

    if method == 'min_variance':
        res = minimize(fun1, x0, bounds=bnds, constraints=cons, method='SLSQP', options=options)
    elif method == 'risk_parity':
        res = minimize(fun2, x0, bounds=bnds, constraints=cons, method='SLSQP', options=options)
    elif method == 'max_diversification':
        res = minimize(fun3, x0, bounds=bnds, constraints=cons, method='SLSQP', options=options)
    elif method == 'equal_weight':
        return pd.Series(index=cov_mat.index, data=1.0 / cov_mat.shape[0])
    elif method == 'mean_var':
        res = minimize(fun4, x0, bounds=bnds, constraints=cons, method='SLSQP', options=options)
    elif method == 'target_maxdown':
        cons = ({'type': 'eq', 'fun': lambda x: sum(x) - 1},
                {'type': 'eq', 'fun': lambda x: -MaxDrawdown((x*returnDf).sum(axis=1))+assetMaxDown})
        res = minimize(fun5, x0, bounds=bnds, constraints=cons, method='SLSQP', options=options,tol=1e-5)
    elif method == 'target_risk':
        cons = ({'type': 'eq', 'fun': lambda x: sum(x) - 1},{'type': 'eq', 'fun': lambda x: fun1(x)[0,0]*250-assetVar}
                )#,
        res = minimize(fun5, x0, bounds=bnds, constraints=cons, method='SLSQP', options=options)
    else:
        raise ValueError('method should be min variance/risk parity/max diversification/equal weight！！！')

    # 权重调整
    if res['success'] == False:
        print("minize result：",res['message'])
        pass
    wts = pd.Series(index=cov_mat.index, data=res['x'])
    if wts_adjusted == True:
        wts = wts[wts >= 0.0001]
        return wts / wts.sum() * 1.0
    elif wts_adjusted == False:
        return wts
    else:
        raise ValueError('wts_adjusted should be True/False！')