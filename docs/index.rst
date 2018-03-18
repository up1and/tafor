.. tafor documentation master file, created by
   sphinx-quickstart on Sun Mar 18 14:53:59 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

欢迎浏览 Tafor 的文档
=================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

本软件用于民航气象部门智能发布预报报文、趋势报文、重要气象情报，监控预报报文，以声音或电话的方式返回告警

主要功能
----------
- TAF 报文编辑
    - 报文验证
        - 单项输入字符验证
        - 温度组的验证
        - 云组的验证
        - 报文的逻辑验证（包括能见度和天气现象、天气现象和云组的验证）
    - 添加 BECMG 或 TEMPO 变化组
    - 生成 AMD 或 COR 报文
    - 生成取消报
- TREND 报文编辑
- SIGMET 报文编辑
    - 模板编辑（WS，WC）
    - 自定义编辑
    - 生成取消报
- 监控与告警
    - 自动查询 METAR 报文
    - 自动查询 TAF 报文入库状态及字符正确
    - TAF 报文迟发告警
    - SIGMET 报文发布提醒
    - TREND 报文发布提醒
    - TAF 报文发布提醒
    - 迟发报文提供电话和声音的告警

预览
----------
.. image:: /images/home.png


安装
----------
- 操作系统限制为 Windows 7 SP1 以上
- 遇到缺失 `api-ms-win-crt-runtime-l1-1-0.dll`，请确保安装 `Microsoft Visual C++ 2015 Redistriuutaule`

参考
----------
- `TAF Decode <https://www.aviationweather.gov/static/help/taf-decode.php>`_
- `SIGMET Introduction <https://en.wikipedia.org/wiki/SIGMET>`_


索引

* :ref:`genindex`
* :ref:`search`
