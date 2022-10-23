.. _intro:

简介
=============

Tafor 支持复杂 TAF 报文的逻辑验证，趋势校验，SIGMET 图形化编发和解析。

功能介绍
----------

Tafor 用于发布民航气象报文，包括 TAF 报文、趋势报文和 SIGMET。

TAF 报文编辑的验证规则适用于中国民用航空气象预报手册，可以防止字符错误，识别复杂天气之间的转折逻辑，最大限度纠错。

SIGMET 报文以 ASIA/PACIFIC REGIONAL SIGMET GUIDE NINTH EDITION 为标准， 可以图形化编辑和解析 SIGMET，受香港天文台 SIGMET 协同平台的启发。

SIGMET 提供了通知接口可以接收香港天文台 SIGMET 协同平台的报文，用于多个情报区之间协同发布 SIGMET。

趋势预报提供了接口可以供观测发报软件用于趋势校验和实时显示观测用户预发的报文。

规格详述
----------

目录结构
^^^^^^^^^^

Tafor 采取便携的安装方式，可以放置在任意目录下，结构如下::

    |-- i18n
        |-- zh_CN.qm
    |-- sounds
        |-- alarm.wav
        |-- notification.wav
        |-- notification-incoming.wav
        |-- taf.wav
        |-- sigmet.wav
        |-- trend.wav
    |-- db.sqlite3
    |-- tafor.exe
    |-- tafor.log


- :file:`i18n/zh_CN.qm` 用于加载中文语言，如果不存在载入的默认语言是 English 
- :file:`sounds` 文件夹中包含内置的提醒声音，包括闹钟等提醒声音，可以随意替换，但必须是 `wav` 类型的文件
- :file:`db.sqlite3` sqlite 数据库文件，日常的报文数据储存在这里，如果不存在程序会在启动时创建
- :file:`tafor.exe` 程序执行文件
- :file:`tafor.log` 日志文件，最大保存 5M，单个文件最大 1M，日志会在运行时创建

编码格式
^^^^^^^^^^

Tafor 使用标准的 ASCII [#ascii]_ 发送报文，在业内也俗称 ITA5。另一种业内使用的编码 ITA2 [#ita2]_ 可以启用，但是为实验性质功能，传输格式为 HexBytes。

Tafor 发送的 AFTN 报文格式如下::

        ZCZC LAA0001
        GG OPKCZQZX
        120900 OPKCZQZX
        MESSAGE TEXT



        NNNN

每行换行符由 `CRLF` 组成 [#newline]_ ，报文的正文和结尾 ``NNNN`` 之间间隔 4 个 `CRLF`，两份相连的报文之间用 4 个 `CRLF` 做区分。

另一种文件格式的报文，可以通过 FTP 服务器转发，文件名根据当前时间生成，类似 ``M120190630075200320.TXT``，内容格式如下::

        ZCZC 001
        MESSAGE TEXT



        NNNN

文件格式的报文流转会以转发服务器设置的地址为准。

.. note:: 生产环境中无论换行符只用 `LF` 或者 `CRLF`，甚至和转报系统预设的匹配格式换行数不一样，都对入库解析无影响，具体实际情况还是以当地的测试为准。


.. [#ascii] ASCII https://en.wikipedia.org/wiki/ASCII
.. [#ita2] ITA2 (Baudot–Murray code) https://en.wikipedia.org/wiki/Baudot_code#ITA2
.. [#newline] Carriage Return 简称 CR，Line Feed 简称 LF
