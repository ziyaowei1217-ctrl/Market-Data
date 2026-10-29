"""Transparent chart calculations and typed inputs; no financial model inference."""
from pathlib import Path
import csv
import json
import numpy as np
import pandas as pd

DERIVED = ['drawdown','volatility','rolling_correlation','correlation','risk_return','distribution','calendar','relative']
TABLES = ['candlestick','waterfall','football','sensitivity','flows','valuation']
STREET = ['drawdown','volatility','rolling_correlation','correlation','risk_return','distribution',
          'candlestick','relative','calendar','flows','valuation','football','waterfall','sensitivity']


def daily_returns(frame):
    return frame.pct_change(fill_method=None)


def drawdowns(frame):
    return (frame / frame.cummax() - 1) * 100


def rolling_volatility(frame, window=21, annualization=252):
    return daily_returns(frame).rolling(window, min_periods=window).std(ddof=1) * np.sqrt(annualization) * 100


def relative_performance(frame, benchmark):
    common=frame.dropna(how='any')
    if benchmark not in frame or common.empty:
        raise ValueError('相对表现需要有效基准资产及共同起始日。')
    subset=frame.loc[common.index[0]:]
    ratios=subset.div(subset[benchmark],axis=0)
    if len(ratios)<2 or (ratios.count()<2).any():
        raise ValueError('相对表现需要共同基准日之后每个资产至少两个有效比值。')
    return ratios.div(ratios.iloc[0]) * 100


def calendar_returns(series, cutoff):
    series=series.loc[:pd.Timestamp(cutoff)]
    month_end=series.resample('ME').agg(lambda values: values.iloc[-1] if len(values) else np.nan)
    change=month_end.pct_change(fill_method=None)*100
    # First observed month has no prior-month endpoint and remains N/A.
    years=sorted(set(change.index.year))[-8:]
    result=pd.DataFrame(np.nan,index=years,columns=range(1,13))
    for date,value in change.items():
        if date.year in years:
            result.loc[date.year,date.month]=value
    return result


def validate_table(key, frame, cutoff):
    frame=frame.copy()
    if frame.empty or frame.columns.has_duplicates:
        raise ValueError(f'{key}: 表不能为空，列名不能重复。')
    specs={'candlestick':['date','open','high','low','close','volume'],
           'waterfall':['label','value','kind'], 'football':['label','low','high'],
           'valuation':['date','actual','lower','upper']}
    required=specs.get(key, ['date'] if key=='flows' else ['scenario'])
    if any(column not in frame for column in required):
        raise ValueError(f'{key}: 缺少列 {required}')
    if key in ('candlestick','valuation','flows'):
        dates=pd.to_datetime(frame.pop('date'),format='%Y-%m-%d',errors='raise')
        if dates.isna().any() or dates.duplicated().any() or dates.dt.tz is not None:
            raise ValueError(f'{key}: 日期不能为空、重复或带时区。')
        frame.index=pd.DatetimeIndex(dates)
        frame=frame.sort_index().loc[:pd.Timestamp(cutoff)]
        if len(frame)<2:
            raise ValueError(f'{key}: 截止日之前至少需要两行。')
    if key in ('football','waterfall','sensitivity'):
        labels=frame['scenario' if key=='sensitivity' else 'label']
        if labels.isna().any() or labels.duplicated().any() or any(not isinstance(x,str) or not x.strip() or len(x)>12 for x in labels):
            raise ValueError(f'{key}: 标签需唯一，长度 1–12。')
        if not 1<=len(frame)<=8:
            raise ValueError(f'{key}: 支持 1–8 行。')
    metadata_columns={'waterfall':['label','kind'],'football':['label'],'sensitivity':['scenario']}.get(key,[])
    numbers=frame.drop(columns=metadata_columns)
    numbers=numbers.apply(pd.to_numeric,errors='raise')
    if not np.isfinite(numbers.to_numpy(dtype=float)).all():
        raise ValueError(f'{key}: 数字不能为空或无穷值。')
    frame[numbers.columns]=numbers
    if key=='candlestick':
        if (frame[['open','high','low','close']]<=0).any().any() or (frame.volume<0).any():
            raise ValueError('OHLC 价格必须为正，成交量不能为负。')
        if (frame.high<frame[['open','low','close']].max(axis=1)).any() or (frame.low>frame[['open','high','close']].min(axis=1)).any():
            raise ValueError('OHLC 必须满足 low ≤ open/close ≤ high。')
    elif key=='waterfall':
        if len(frame)<3 or frame.kind.iloc[0]!='total' or frame.kind.iloc[-1]!='total' or not (frame.kind.iloc[1:-1]=='change').all():
            raise ValueError('瀑布图必须是 total、若干 change、total。')
        if not np.isclose(frame.value.iloc[0]+frame.value.iloc[1:-1].sum(),frame.value.iloc[-1],rtol=1e-8,atol=1e-8):
            raise ValueError('瀑布图期初加变动必须等于期末。')
    elif key=='football':
        if (frame.low>frame.high).any(): raise ValueError('估值区间 low 必须 ≤ high。')
    elif key=='valuation':
        if (frame.lower>frame.upper).any(): raise ValueError('估值带 lower 必须 ≤ upper。')
    elif key=='sensitivity':
        if not 2<=len(frame.columns)<=8: raise ValueError('敏感性表支持 1–7 个数值列。')
        if any(len(str(c))>12 for c in numbers.columns): raise ValueError('敏感性列标签最多 12 字符。')
    elif key=='flows':
        if not 1<=len(frame.columns)<=4 or len(frame)>24: raise ValueError('资金流支持 1–4 类别、最多24期。')
        if any(len(str(c))>12 for c in frame.columns): raise ValueError('资金流类别名称最多12字符。')
    return frame


def load_bundle(folder, cutoff):
    result={}
    for key in TABLES:
        path=Path(folder)/f'{key}.csv'
        if not path.exists(): continue
        with path.open(encoding='utf-8-sig',newline='') as handle:
            names=next(csv.reader(handle),[])
        if not names or len(set(names))!=len(names) or any(not n.strip() for n in names):
            raise ValueError(f'{key}: CSV 列名不能重复或为空。')
        result[key]=validate_table(key,pd.read_csv(path),cutoff)
    return result


def prepare(key, frame, tables, meta):
    if key in TABLES:
        if key not in tables: raise ValueError(f'{key} 需要 --bundle 中的 {key}.csv')
        unit=meta.get('chart_units',{}).get(key)
        if not isinstance(unit,str) or not unit.strip() or len(unit)>24:
            raise ValueError(f'请在 chart_units.{key} 指定单位（1–24字符）。')
        if key=='sensitivity':
            digits=meta.get('sensitivity_decimals',2)
            if isinstance(digits,bool) or not isinstance(digits,int) or not 0<=digits<=6:
                raise ValueError('sensitivity_decimals 必须为 0–6 的整数。')
        return tables[key]
    if frame is None: raise ValueError(f'{key} 需要资产价格 --csv')
    focus=meta.get('focus_asset',frame.columns[0])
    benchmark=meta.get('benchmark',frame.columns[0])
    if focus not in frame or benchmark not in frame: raise ValueError('focus_asset / benchmark 不在资产列中。')
    annual=meta.get('annualization',252)
    if isinstance(annual,bool) or not isinstance(annual,(int,float)) or not np.isfinite(annual) or annual<=0:
        raise ValueError('annualization 必须为正数。')
    rets=daily_returns(frame)
    if key=='drawdown': return drawdowns(frame)
    if key=='relative': return relative_performance(frame,benchmark)
    if key=='calendar':
        result=calendar_returns(frame[focus],meta['as_of'])
        if not result.notna().any().any(): raise ValueError('月度收益图至少需要两个相邻月份的价格。')
        return result
    if key=='volatility':
        result=rolling_volatility(frame,21,annual)
        if (result.count()<2).any(): raise ValueError('波动率图每个资产至少需要两个完整21期收益窗口。')
        return result
    if key=='rolling_correlation':
        pair=meta.get('correlation_pair',list(frame.columns[:2]))
        if len(pair)!=2 or pair[0]==pair[1] or any(v not in frame for v in pair):
            raise ValueError('correlation_pair 需要两个不同的资产名称。')
        result=rets[pair[0]].rolling(60,min_periods=60).corr(rets[pair[1]]).clip(-1,1)
        if result.count()<2: raise ValueError('滚动相关性至少需要两个完整60期窗口；常数收益无法计算。')
        return result
    if key=='distribution':
        result=rets[focus].dropna()*100
        if len(result)<20: raise ValueError('收益分布至少需要20个有效收益观察值。')
        return result
    complete=rets.dropna(how='any')
    if len(complete)<20: raise ValueError('风险/相关性分析至少需要20个共同收益观察值。')
    if key=='correlation': return complete.corr()
    if key=='risk_return':
        return pd.DataFrame({'risk':complete.std(ddof=1)*np.sqrt(annual)*100,'return':complete.mean()*annual*100})
    raise ValueError(f'未知图表 {key}')


def create_street_demo(folder):
    folder=Path(folder)
    rng=np.random.default_rng(823)
    dates=pd.bdate_range('2026-08-03','2026-10-23')
    close=100*np.exp(np.cumsum(rng.normal(.001,.01,len(dates))))
    opens=close*(1+rng.normal(0,.005,len(dates)))
    frame=pd.DataFrame({'date':dates,'open':opens,'high':np.maximum(opens,close)*(1+rng.uniform(.001,.015,len(dates))),
                        'low':np.minimum(opens,close)*(1-rng.uniform(.001,.015,len(dates))),
                        'close':close,'volume':rng.integers(500000,3000000,len(dates))})
    frame.to_csv(folder/'candlestick.csv',index=False)
    pd.DataFrame({'label':['期初利润','销量','价格','原料成本','运营费用','期末利润'],
                  'value':[100,25,18,-12,-8,123],'kind':['total','change','change','change','change','total']}).to_csv(folder/'waterfall.csv',index=False)
    pd.DataFrame({'label':['可比公司','先例交易','现金流折现','杠杆收购'],
                  'low':[85,100,93,78],'high':[113,132,125,103]}).to_csv(folder/'football.csv',index=False)
    pd.DataFrame({'scenario':['g = 1.0%','g = 1.5%','g = 2.0%','g = 2.5%','g = 3.0%'],
                  '7.0%':[116,123,132,142,154],'8.0%':[100,106,113,120,129],
                  '9.0%':[88,93,98,104,111],'10.0%':[78,82,87,92,97],'11.0%':[70,74,78,82,86]}).to_csv(folder/'sensitivity.csv',index=False)
    flowdates=pd.date_range('2026-08-07','2026-10-23',freq='W-FRI')
    pd.DataFrame({'date':flowdates,'股票':rng.normal(2,3,len(flowdates)),'债券':rng.normal(1,2,len(flowdates)),
                  '货币市场':rng.normal(2,2,len(flowdates))}).to_csv(folder/'flows.csv',index=False)
    vdates=pd.bdate_range('2025-10-24','2026-10-23')
    center=np.linspace(17,19,len(vdates))
    actual=center+np.sin(np.linspace(0,8,len(vdates)))*2+rng.normal(0,.18,len(vdates))
    pd.DataFrame({'date':vdates,'actual':actual,'lower':center-1.5,'upper':center+1.5}).to_csv(folder/'valuation.csv',index=False)
    path=folder/'metadata.json'; meta=json.loads(path.read_text(encoding='utf-8'))
    meta.update(focus_asset='美国股票',benchmark='美国股票',highlight=['美国股票','黄金'],correlation_pair=['美国股票','美国国债'],annualization=252,
                chart_units={'candlestick':'USD / 股；成交量：股','waterfall':'USD mn','football':'USD / 股',
                             'sensitivity':'USD / 股；列为 WACC','flows':'USD bn','valuation':'远期 P/E（倍）'})
    meta['source']='模拟数据 · 固定种子24 / 625 / 823'
    path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
