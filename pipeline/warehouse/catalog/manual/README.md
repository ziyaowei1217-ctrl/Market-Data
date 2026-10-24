# 人工维护数据

`method = manual` 的指标（央行会议日期、BoJ/智利/土耳其政策利率、选举日期、财政截止日等）
没有稳定的免费接口，按官方公告人工维护在本目录的 CSV 中，再由流水线写入数据库。

CSV 格式：`series_key,obs_date,value,source_url,note`，一行一次官方公告；
日期类指标的 value 写成 `YYYYMMDD` 数字，note 写原文。只录入已正式公告的信息，
不录入预测或传闻。
