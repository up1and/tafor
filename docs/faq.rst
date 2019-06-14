.. _faq:

常见问题
=================================

这里举例说明一些常见的，但使用说明中没有提及的问题。


#. 如果在天气现象中添加一些行业标准中不存在的天气现象，并且在 TAF 报文中选用，会发生什么？

   行业标准中不存在的天气现象会被验证程序过滤掉，在 TAF 报文预览界面会有灰色文字，提示经过校验后的报文和原始报文有些不同。

   趋势编辑预览不会做这种过滤。

#. 为什么 TAF 报文的预览部分错误没有文字提示，只有错误的项会标红提示？

   这是由行业标准的验证机制决定的，举例来说，风组的判定条件主要有 3 条，如果都不满足 1、 2、 3 程序才会认定不符合标准，这么一大段文字描述不适合放置在预览框里。

   不过两种以上的天气组合会有文字提示。

#. 在发送报文界面，点击发送按钮报文没有正常发出，这里的重发按钮和 TAF 报文数据展示页的重发按钮有什么不同？

   如果在发送界面点击发送后弹出发送失败的错误提示，往往说明串口参数配置有错，导致报文还没有发送到转报系统，所以此时点击发送，会把之前的 AFTN 报文一字不改的重新发送。

   如果已正常发报，由于一些特殊的原因，系统没有正确的查询到已发报文，这时的重发按钮会重新加载一个预览界面，重新发送会更新 AFTN 报文中的流水号和日时组，报文主体内容不变，重新发往转报系统。

#. 为什么在无法加载远程的情报区信息后，用户无法图形化编辑 SIGMET 了？

   情报区信息每一个地方都不相同，这些信息不适合写死在程序里。所以采取远程热更新的方式来加载。

   如果没有云图底图的经纬度信息，像素大小，无法将鼠标指向的点换算成经纬度。

#. 报文的数据源不更新，云图底图长时间不更新或无法加载云图底图怎么办？

   首先要确定网络状态和设置是否都正确。

   在设置 -> 监控 -> 报文地址或情报区信息地址一栏中，将地址复制到浏览器内看能否正常打开。
    
   如果出现 ``502 Bad Gateway``、``404 Not Found`` 之类的字样，请仔细检查 :ref:`install` 中数据源的部署是否正常。

   情报区信息出错会出现一种特殊情况，情报区信息地址可以正常加载，但其中的 ``image`` 字段值为 ``null``，这时请检查接入的第三方云图是否正常。

   查看软件运行日志也能找到原因。

#. 编辑 SIGMET 时简化后的图形超过情报区边界是否可以？

   根据 `ASIA/PACIFIC REGIONAL SIGMET GUIDE SIXTH EDITION ― MAY 2017, APPENDIX B, Annex 3` [#polygons_with_complex_boundaries]_ 的解释，为了简化复杂边界的多边形，多边形可以向外延伸包含所画边界内所有的点。

   如果准备发布的 SIGMET 区域和相邻的情报区有交集，最好和当地的气象监视台沟通。

#. 发出去的报文流水号和转报系统中的流水号不匹配会发生什么？

   比如转报系统中的当前流水号是 3，发出的报文流水号是 5，转报系统会报错，但报文仍会被正常转发。转报系统下一份流水号会从 6 算起。


.. [#polygons_with_complex_boundaries] Some FIR boundaries are complex, and it would be unrealistic to expect that a polygon would be defined that followed such boundaries precisely. As such, some States have determined that the polygon points be chosen in relation to the complex boundary such that the FIR boundary approximates, but is wholly encompassed by, the polygon, and that any additional area beyond the FIR boundary be the minimum that can be reasonably and practically described. Caution should however be exercised in those instances where international aerodromes are located in close proximity to such a complex FIR boundary.
