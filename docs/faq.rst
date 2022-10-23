.. _faq:

常见问题
=================================

这里举例说明一些常见的，但使用说明中没有提及的问题。


#. 如果在天气现象中添加一些行业标准中不存在的天气现象，并且在 TAF 报文中选用，会发生什么？

   行业标准中不存在的天气现象会被验证程序过滤掉，在 TAF 报文预览界面会有灰色文字，提示经过校验后的报文和原始报文有些不同。

#. 报文的数据源不更新，图层底图长时间不更新或无法加载底图怎么办？

   请先尝试按 **刷新按钮** 刷新图层。

   如果仍无法加载图层，要确定网络状态和设置是否都正确。

   在设置 -> 数据源 -> 报文地址或图层地址一栏中，将地址复制到浏览器内看能否正常打开。
    
   如果出现 ``502 Bad Gateway``、``404 Not Found`` 之类的字样，请仔细检查 :ref:`install` 中数据源的部署是否正常。

   图层信息出错有一种特殊情况，图层信息可以正常加载，但其中的 ``image`` 字段值为 ``null``，这时请检查接入的图片储存服务是否正常。

   查看软件运行日志找原因。

#. 编辑 SIGMET 时简化后的图形超过情报区边界是否可以？

   根据 `ASIA/PACIFIC REGIONAL SIGMET GUIDE NINTH EDITION, APPENDIX B, Annex 3` [#polygons_with_complex_boundaries]_ 的解释，为了简化复杂边界的多边形，多边形可以向外延伸包含所画边界内所有的点。

   如果准备发布的 SIGMET 区域和相邻的情报区有交集，最好和当地的气象监视台沟通。

#. 发出去的报文流水号和转报系统中的流水号不匹配会发生什么？

   比如转报系统中的当前流水号是 3，发出的报文流水号是 5，转报系统会报错，但报文仍会被正常转发。转报系统下一份流水号会从 6 算起。


.. [#polygons_with_complex_boundaries] Some FIR boundaries are complex, and it would be unrealistic to expect that a polygon would be defined that followed such boundaries precisely. As such, some States have determined that the polygon points be chosen in relation to the complex boundary such that the FIR boundary approximates, but is wholly encompassed by, the polygon, and that any additional area beyond the FIR boundary be the minimum that can be reasonably and practically described. Caution should however be exercised in those instances where international aerodromes are located in close proximity to such a complex FIR boundary.
