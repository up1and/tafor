.. _guide:

使用指南
=================================

主界面
----------

总览
^^^^^^^^^^^

.. image:: /images/main.png

主界面有五个标签页，分别对应着不同的数据展示：

- **RECENT** 显示每一个类别中 24 小时内的最新报文，以及用虚线框显示观测的通知报文
- **TAF** 以表格的形式展示历史预报报文，包含数据源查询状态
- **METAR** 以表格的形式展示历史观测
- **SIGMET** 以表格的形式展示历史重要气象情报
- **AIRMET** 以表格的形式展示历史低空气象情报

RECENT 页面 SIGMET 展示栏会显示当前报文的图形区域，右上角的闹钟图标闹钟状态，可以开启或者关闭。

数据展示
^^^^^^^^^^^

.. image:: /images/taf_table.png

表格数据每一页显示 12 条，其中 SIGMET 每页展示 6 条，双击表格区域可以复制报文内容。

表格数据中只有 TAF 标签页有查询一栏，``绿色对勾`` 代表发送的报文已和远程数据源对比，数据一致，``灰色问号`` 代表发送的报文远程数据源还没有查到或者远程数据源和本地发出的报文数据不一致。

表格右下角区域为功能区，不同类型的报文功能区按钮会有些不同。

- ``信息图标`` 可以查看已发过的报文

- ``导出图标`` 可以将历史报文数据导出为 CSV 格式的文件，可自定义选择导出时间范围

- ``搜索图标`` 点击图标可根据日历查询任意一天的历史报文，搜索框支持按关键字过滤报文

- ``图表图标`` 观测报文可以以图表的方式查看，方便快速查看各气象要素的变化

- ``蓝色箭头`` 为翻页按钮

.. note:: TAF 报文在发送后没有出现绿色对勾的标志，请务必检查报文是否正确发出。


报文详情
^^^^^^^^^^^

.. image:: /images/view_message.png

在数据展示窗口选中报文后点击 ``蓝色信息图标`` 可查看报文详情，查看 SIGMET 原始数据区域会被替换为 SIGMET 的图形区域。

本地发出的报文可以打印气象情报发布单，可适用于应急处理。

如果报文发布后没有被自动查到，2 个小时内，可以重新发送此报文。

.. note:: 如果在发送的过程中程序有错误提示，例如本机串口原因，重新发送 AFTN 报文会原样送出；如果报文已通过本机正常发出，但库中并未查到，重新发送 AFTN 报文日时组和流水号会重新生成。

观测图表
^^^^^^^^^^^

.. image:: /images/chart.png

观测图表可以根据历史观测报文绘制重要气象要素的变化，有风、能见度、天气现象、云、温度露点、修正海平面气压六种图表。

鼠标移至图表绘制点附近，会有标签显示详细数值。

左上角日期可以自行输入或通过下拉菜单用日历选择，时间范围也可以通过右上角的 ``-1 天``、``-3 小时``、 ``+3 小时``、``+1 天`` 调整。

``保存`` 按钮可以把图表储存为图片，文件名会根据日期自动确定。


设置
----------

常规
^^^^^^^^^^^

.. image:: /images/general_settings.png

通用
""""""""""""
- **窗口风格** 设置窗口主题，默认跟随系统
- **界面大小** 调整界面放大比例，普通 100%，大 125%，最大 150%
- **通讯协议** 报文生成规格，默认生成 TAC 类型的报文由串口发往 AFTN 网络，特殊情况可以选择通过 FTP 发布
- **预报报文规格** TAF 报文的规格类型，时长可选择 9 时制、 24 时制和 30 时制，其中 9 时制生成 FC 类型的报文，24 时制和 30 时制生成 FT 类型的报文
- **开机自动启动** 程序在系统启动时自动启动
- **变化组时间自动补全** 勾选后 TAF 报文变化组会根据起始时间自动补全结束时间，BECMG 组结束时间递增 1 小时， TEMPO 组结束时间根据报文类型的不同递增 4 或 6 小时
- **启用调试模式** 勾选后用于开启低级别的日志记录模式

备份
""""""""""""
设置导入导出支持 JSON 格式的配置文件，部分配置样例如下：

.. code-block:: json

    {
      "Message/Airport":"ZJHK",
      "Interface/MessageURL":"https://tafor-scripts.vercel.app/messages/zjhk",
      "Communication/SerialPort":"COM1",
      "Message/WeatherWithIntensity":"[\"RA\", \"SHRA\", \"TSRA\", \"SHGRRA\"]",
      "General/Debug":"true"
    }

载入配置文件时，先点击 ``浏览`` 选择配置文件，再点击 ``导入`` 按钮。

备份配置文件时，先点击 ``浏览`` 选择导出目录，再点击 ``导出`` 按钮。

.. note:: 导入配置文件后会覆盖本机当前设置，使用时请注意备份好数据。


报文
^^^^^^^^^^^

.. image:: /images/message_settings.png

报文前缀
""""""""""""

- **机场代码** 本地机场的 ICAO 机场代码，如 ZJHK
- **公报编号** 本地机场的区域和公报编号，如 CI35
- **飞行情报区名称** 用于发布 SIGMET 的关键参数，比如 ZJSA SANYA FIR
- **趋势识别码** 观测发报软件和预报发报软件约定的一个特殊字符，用于识别趋势预报内容，具体依情况而定


天气现象
""""""""""""

天气现象的添加分为两组，有强度变化的和无强度变化的，有强度变化的天气现象无需再添加强度符号。

天气现象之间的顺序可以通过拖动后改变。

天气现象只能添加行业标准里有的天气现象，不能添加奇怪的字符，字符必须大写。

.. note:: 天气现象有变更需要重新启动才能生效。


通信
^^^^^^^^^^^
.. image:: /images/communication_settings.png


串口参数
""""""""""""
串口参数请根据实际环境填写，用于和本机电流环通信。


AFTN 参数
""""""""""""
- **线路冠字** AFTN 线路的信道
- **流水号** 当日此线路发送的报文序号，世界时日届流水号会重置为 1
- **流水号位** 流水号的最大位数，如选择 3 位，流水号会补全为 001， 4 位则为 0001
- **用户单位** 报文的发报源头
- **地址上限** AFTN 转报机一份报文允许最大的地址上限，通常一份报文支持 21 个地址，最多 3 行地址，每行不超过 7 个地址

.. note:: AFTN 参数的配置请以实际环境为主，参数的不同会影响到最终发送的报文段行不同。


FTP 参数
""""""""""""

请以 ``ftp://user:password@host:port/path`` 的标准格式填入，端口为默认端口 21 时可以省略。

登录按钮可用于测试填入的 FTP 信息是否正确，不会发送任何内容。

.. note:: 部分地区可以使用 FTP 通讯机备份发报，发送后程序会生成一份 ``M120190607110758721.TXT`` 以当前时间为准的文本文件，放在指定的主机目录。


发报地址
""""""""""""
不同类别的报文有不同的发报地址，多个发报地址请以空格隔开。


接口
^^^^^^^^^^^

.. image:: /images/interface_settings.png

数据源
""""""""""""
软件会定时请求数据源，获取报文或者图层信息等。

**报文地址**

程序每分钟会请求报文信息，核对远程数据是否与本地数据相同，自动查验报文是否发送成功， 更多信息请查看 :ref:`interface`。

**图层地址**

程序会每 2 分钟请求图层信息，更新 SIGMET 画布的底图， 更多信息请查看 :ref:`interface`。

后台服务
""""""""""""
**后台服务** 勾选后用开启后台服务，默认监听端口 9407，可用启用 webui，接收 SIGMET 报文，趋势报文等功能， 更多信息请查看 :ref:`interface`

**主机** 显示当前主机的地址和端口

**认证** 接口认证令牌，可复制到剪贴板，也可点击重新生成，另外程序运行目录命令行下输入 ``tafor token --generate`` 也可用于重新生成令牌，建议在初次设置后重新生成令牌。


监控
^^^^^^^^^^^

.. image:: /images/monitor_settings.png

迟发监控
""""""""""""
监控 TAF 报文的正常发布情况，只关注正常报，默认以声音的方式返回告警。

告警时间填写范围 0 - 50，默认值为30，时间单位为分钟。


.. note:: 举例 FC0312 发报时间为 01:00 - 01:50 之间，如果设置告警时间为 30，再 01:30 之后如果 FC0312 报文还未正常发出，警告就会触发。


声音提醒和音量
"""""""""""""""
**预报**

整点发报时间之后的 5 分钟，会弹出闹钟提醒发报，闹钟有贪睡和关闭功能，贪睡的功能为 5 分钟后再此提醒你。

如果在此期间，报文已经成功发布并且远程数据源也已确认，该时次闹钟不会再响起。


**趋势**

趋势预报的提醒主要以嘀嗒的声音为主，触发时间范围为正点的前三分钟到整点，通知接口接收到新的观测报文时，声音也会触发。


**重要气象情报**

发布一种类型的重要气象情报后会自动添加一个闹钟，在重要气象情报有效期结束前 20 分钟时闹钟响起，提醒你是否需要继续发布重要气象情报。

取消报不会自动添加闹钟，同时会取消被取消报的闹钟。


验证
^^^^^^^^^^^

.. image:: /images/validation_settings.png

预报和趋势
""""""""""""
开启个性化校验 TAF 和趋势的校验规则

图层
^^^^^^^^^^^

.. image:: /images/layer_settings.png

投影
""""""""""""
SIGMET 画布的投影参数，支持 proj string，如常见的投影参数：

等经纬度投影 ``+proj=eqc``

Web 麦卡托投影 ``+proj=webmerc +datum=WGS84``

飞行情报区边界
""""""""""""""""
在 SIGMET 画布中绘制情报区边界，需要添加一系列的坐标点，`[lon, lat]`，JSON 格式，样例如下：

.. code-block:: json

    [
        [
            114.000001907, 
            14.500001907
        ], 
        [
            112.000001908, 
            14.500001907
        ], 
        [
            108.716665268, 
            17.416666031
        ], 
        [
            107.683332443, 
            18.333333969
        ], 
        [
            107.18972222, 
            19.26777778
        ], 
        [
            107.929967, 
            19.9567
        ], 
        [
            108.050001145, 
            20.500001907
        ], 
        [
            111.500001908, 
            20.500001907
        ], 
        [
            111.500001908, 
            19.500001907
        ], 
        [
            114.000001907, 
            16.666666031
        ], 
        [
            114.000001907, 
            14.500001907
        ]
    ]


.. note:: 部分配置更改需重启软件，保存后会提示。


TAF 报文的编辑
--------------

编辑
^^^^^^^^^^^

.. image:: /images/taf_editor.png

``箭头`` 按钮可以使报文的有效期变为前一个时次，使用前置操作时请一定要留意报文有效时段的变化，``重置`` 按钮会将报文有效期还原到默认时次。

阵风、能见度、温度的输入需要手动补 0，比如阵风 9 m，需要输入 09。

云组的第一项输入 VV，可切换为垂直能见度模式，删除 VV 后切换为云组。

有效期 30 小时的报文会出现三组温度组，其中最后一组温度组可以点击 **温度计** 图标切换最高温模式或最低温模式。可变温度组不强制要求输入。在三组温度组模式中，温度组会按照高温优先并以时间排序，校验时遵循，两个最高温或最低温不能出现在同一天。

变化组会按照 BECMG 组在前，TEMPO 组在后并以起始时间排序。

编辑框严格限制了每项要素所能输入的字符，未输入完全的项会灰色显示，所有必要项输入完全后，才可以进行下一步。

预览和校验
^^^^^^^^^^^

.. image:: /images/taf_preview.png

预报报文校验可以实现复杂逻辑的校验，比如 TEMPO 跨越多个 BECMG 组的检验。

预报报文转折逻辑有误，会用红色高亮显示，单项要素之间的转折判断不会标注不符合规则的原因，只有涉及多项要素之间的组合才会有文字提示。

如果报文没有通过预设校验依旧可以发布报文，但会有二次确认对话框。

根据通讯协议的设置，右上角会显示当前报文会通过何种方式发送，如果不是常用的 AFTN 线路，发送时会有二次提醒。

.. note:: 校验程序会过滤一些不在行业标准中的字符，预览时如果有提示 `经过校验后的报文和原始报文有些不同`，请仔细检查报文内容。


趋势报文的编辑
-----------------

编辑
^^^^^^^^^^^

.. image:: /images/trend_editor.png

趋势预报选择 FM、TL、AT 时间组时，只能提前 150 分钟添加。

首页会显示最近一次发布的趋势预报，如果最后一条记录是 NOSIG，则不会显示趋势相关信息。

右上侧灰色区域会显示当前正在编辑的观测报文，观测报文的历史数据会保存10分钟，或在新的观测报文入库后失效。

预览
^^^^^^^^^^^

.. image:: /images/trend_preview.png

趋势报文的校验与 TAF 报文校验规则相同。

如果程序收到观测软件发来的观测报文，校验功能会被启用，此时趋势验证会类似 TAF 报文，在本地进行逻辑校验，同时观测报文会以灰色文字显示显示在预览界面。

通知和校验
^^^^^^^^^^^

.. image:: /images/trend_notification.png

观测点击编报后，程序收到来自观测的预发报文，报文显示有效期为 10 分钟，点击右上角回复箭头可以快速发布趋势。

如果通知报文中有加粗字体，代表此气象要素相对于上份发生了变化。

通过预发报文是否带有趋势内容，可以判断观测发报软件的趋势附着状态。

左上角没有图标代表只是一个通知事件，观测发报软件不会做任何操作。

.. image:: /images/trend_validation_pass.png

观测发报软件开启趋势校验功能后通知报文左上角会有图标显示。

趋势校验成功，左上角图标会变为绿色盾形。

.. image:: /images/trend_validation_error.png

趋势校验不成功，左上角图标会变为黄色盾形，趋势内容会有标红或文字提示。此时观测发报软件的趋势会自动变为 NOSIG，如果需要发布新的趋势，请尽快重发。

当查到观测已经发出观测报文后，预发报文状态清零。

.. note:: 显示观测报文和校验功能都需要观测发报软件的配合，而且需要程序在设置中 `启用远程调用接口服务`，接口详情参考 :ref:`interface`。

SIGMET & AIRMET 报文的编辑
--------------------------
模板
^^^^^^^^^^^

通用模板
"""""""""""""""

.. image:: /images/sigmet_general_template_polygon.png

通用模板适用于快速编辑雷暴、积冰、颠簸的重要气象情报。

报文的起始时间、结束时间、发布序号会自动生成。

SIGMET & AIRMET 可以通过画布绘制区域：

画布右上角操作区按钮从左至右分别为，**刷新按钮**、**图层按钮**、**重叠按钮**、**模式按钮**。

画布会每 2 分钟加载一次最新的图层，并且在画布的左下角显示图层的更新时间和图层名称，画布右上角的 **刷新按钮** 可以手动刷新图层；

画布可通过 :kbd:`鼠标滚轮`，:kbd:`鼠标左键双击`，:kbd:`+/- 按钮` 实现放大缩小功能，按住鼠标左键移动可实现画布的拖拽功能。

位置绘制分为两种，初始位置和最终位置，初始位置绘制完成后，点击右上角 **重叠按钮**，当前绘制位置会变更到最终位置。取消选定 **重叠按钮**，会清除最终位置，当前绘制位置会变更到初始位置。

不同类型的位置会用不同的颜色显示，黄色表示初始位置，淡绿色表示最终位置。

位置绘制支持六种方式，多边形，线，经纬度，走廊型，圆形和全区域，点击右上角右一的 **模式按钮** 可在六种状态之间切换。

**图层选项**

.. image:: /images/layers_popup_menu.png

操作区第二个按钮为 **图层按钮**，点击会弹出下拉菜单。

- **裁剪图形** 显示已发布的 SIGMET/AIRMET 时，报文的图形位置可能会超出情报区范围，勾选时会根据情报区的边界裁剪图形
- **最新气象情报** 勾选后会在图层上显示当前区域内有效的 SIGMET/AIRMET 报文

图层主要两种类型，独立图层和混合图层，独立图层只能单独存在，混合图层可以叠加在独立图层之上，可以通过滑块设置透明度。

Himawari IR Clouds，Himawari True Color，Himawari Ash 是独立图层，Sanya FIR Mosaic 是混合图层。

红外云图叠加雷达拼图效果如下：

.. image:: /images/radar_mosaic.png

**多边形**

最大支持 7 个点，虚线表示正在编辑，实线表示编辑完成，点的生成顺序为顺时针方向，最后一个点和初始点相同显式闭合：

    * :kbd:`Ctrl` + :kbd:`鼠标左键` 添加一个点

    * :kbd:`Ctrl` + :kbd:`鼠标右键` 删除前一个点

在已有两个点时，初始点附近点击可以形成闭合区域，用实线表示编辑完成，此时程序会自动计算所选区域和情报区边界的交集，如果交集的点超过 7 个，会自动平滑到 7 个点以内。

.. image:: /images/sigmet_canvas_draw_polygon_extend.png

对于复杂边界，如国界、海岸线等，程序会自动扩展多边形以确保所有的点都包括在简化后的多边形内，如果扩展后的图形不符合你的预期，可以重新绘制多试几次。
      
**线**

线的编辑方式和点的类似，只是在计算交集时不会对点平滑处理，同样，点的的生成顺序为顺时针方向。

**经纬度**

.. image:: /images/sigmet_canvas_draw_rectangular.png

经纬度最多支持 4 条线构成一个区域，略有不同于点和线的编辑方式：

    * :kbd:`Ctrl` + :kbd:`鼠标左键` 添加一个点（左上角），同时按住 :kbd:`鼠标左键` 拖拽不放可以框选区域，松开 :kbd:`鼠标左键` 添加另一个点（右下角），完成位置的绘制

    * :kbd:`Ctrl` + :kbd:`鼠标右键` 删除整个区域

在编辑完成时，如果某条线的长度小于 0.5 度，则该条线不会被编入到报文中。

**走廊区域**

.. image:: /images/sigmet_canvas_draw_corridor.png

基线最大支持 4 个点，用虚线表示，实线表示编辑完成，添加宽度操作鼠标滚轮即可：

    * :kbd:`Ctrl` + :kbd:`鼠标左键` 添加一个点

    * :kbd:`Ctrl` + :kbd:`鼠标右键` 删除宽度或上一个点

    * :kbd:`Ctrl` + :kbd:`鼠标滚轮` 调整图形的宽度

如果区域的中心线和情报区相交成两条折线，选取先绘制的那条线作为基线。

**全部区域**

.. image:: /images/sigmet_canvas_draw_entire.png

选中后即可生成全部区域。

.. image:: /images/sigmet_canvas_decode.png
      
已发送的 SIGMET 在有效期内会在底图中显示，不同类型的 SIGMET 显示为不同颜色，如雷雨显示棕黄色，火山灰显示红色等，图中的数字为 SIGMET 编号。

如果 SIGMET 报文包含两个位置，最终位置会以淡绿色显示。

热带气旋模板
"""""""""""""""
.. image:: /images/sigmet_typhoon_template.png

热带气旋的位置和范围可以通过图形化绘制，选定中心，再添加边界可以绘制一个圆形区域：

    * :kbd:`Ctrl` + :kbd:`鼠标左键` 第一次添加中心点，第二次添加圆的边界，由这两点确定圆的半径

    * :kbd:`Ctrl` + :kbd:`鼠标右键` 删除半径或中心点

    * :kbd:`Ctrl` + :kbd:`鼠标滚轮` 调整圆的半径

输入框中的经纬度、范围会和图形区域同步，但因为精度换算问题，有可能会和画布中显示的些许不同，最终生成的报文以输入框的为准。如果手工输入经纬度，需要自行添加标识符，如 N、E 等。

最终位置的时间默认为有效结束时前之前的整点。

最终位置的经纬度会根据当前的经纬度、移动速度、移动时间差值，使用 Great Circle [#great_circle]_ 计算最终的经纬度。

.. image:: /images/sigmet_canvas_decode_circle.png

有效期内热带气旋类型的 SIGMET 图形区域会以紫色显示显示。

.. note:: 移动时间优先选取 预测时间 - 观测时间，如果没有观测时间，则用 预测时间 - 起始时间 代替。

咨询情报
~~~~~~~~~~~~~~
在有热带气旋生成时，相应的咨询中心会发布热带气旋咨询情报，咨询情报会预告当前热带气旋的移动路径和影响范围。这里以 NORU 为例：

.. code-block::

    FKPQ31 RJTD 270000
    TC ADVISORY
    DTG: 20220927/0000Z
    TCAC: TOKYO
    TC: NORU
    ADVISORY NR: 2022/20
    OBS PSN: 27/0000Z N1530 E11205
    CB: WI N1055 E11150 - N1345 E10655 - N1655 E10655
    - N1845 E11110 - N1605 E11350 - N1355 E11350
    - N1055 E11150
    TOP FL540
    MOV: W 15KT
    INTST CHANGE: INTSF
    C: 950HPA
    MAX WIND: 85KT
    FCST PSN +6 HR: 27/0600Z N1535 E11105
    FCST MAX WIND +6 HR: 90KT
    FCST PSN +12 HR: 27/1200Z N1550 E11020
    FCST MAX WIND +12 HR: 90KT
    FCST PSN +18 HR: 27/1800Z N1550 E10920
    FCST MAX WIND +18 HR: 85KT
    FCST PSN +24 HR: 28/0000Z N1550 E10810
    FCST MAX WIND +24 HR: 75KT
    RMK: NIL
    NXT MSG: 20220927/0600Z=

.. image:: /images/advisory_typhoon.png

在咨询报文输入框输入咨询报文，可根据初始位置和最终位置的选择，生成对应的图形区域，并自动在模板中填入相应的信息。

模板和咨询报界面可以通过右上角 **箭头按钮** 切换。

火山灰模板
"""""""""""""""
.. image:: /images/sigmet_ash_template.png

火山灰报文的发布有两种选择，火山灰云和带有喷发火山信息的火山灰云。

火山灰云在红外云图和可见光云图中并不容易和其他云系区分，在 Ash 组合通道下较容易识别，图中右侧深蓝色云系是火山灰云。

咨询情报
~~~~~~~~~~~~~~
在有火山喷发时，相应的咨询中心会发布火山会咨询情报，咨询情报会预告火山灰云系的影响范围。这里以 `FUKUTOKU-OKA-NO-BA` 为例：

.. code-block::

    FVFE01 RJTD 142100
    VA ADVISORY
    DTG: 20210814/2100Z
    VAAC: TOKYO
    VOLCANO: FUKUTOKU-OKA-NO-BA 284130
    PSN: N2417 E14129
    AREA: JAPAN
    SUMMIT ELEV: -29M
    ADVISORY NR: 2021/16
    INFO SOURCE: HIMAWARI-8
    AVIATION COLOUR CODE: NIL
    ERUPTION DETAILS: VA EMISSIONS CONTINUING
    OBS VA DTG: 14/2020Z
    OBS VA CLD: SFC/FL480 N2433 E14132 - N2411 E14137 - N2106 E13408 -
    N2030 E12501 - N1829 E11931 - N2032 E11751 - N2342 E12603 - N2314
    E13222 MOV W 55KT
    FCST VA CLD +6 HR: 15/0220Z SFC/FL510 N2533 E14014 - N2412 E14141 -
    N2214 E13836 - N2050 E13001 - N2008 E12142 - N1633 E11431 - N1832
    E11203 - N2402 E12019 - N2355 E13843
    FCST VA CLD +12 HR: 15/0820Z SFC/FL520 N2608 E13902 - N2409 E14145 -
    N2054 E13813 - N2019 E11914 - N1426 E10847 - N1633 E10627 - N2334
    E11717 - N2504 E12425 - N2314 E13600
    FCST VA CLD +18 HR: 15/1420Z SFC/FL530 N2659 E13836 - N2416 E14148 -
    N1936 E13735 - N2050 E12525 - N1846 E11503 - N1134 E10322 - N1259
    E10041 - N2042 E11014 - N2524 E12436 - N2352 E13446
    RMK: NIL
    NXT ADVISORY: 20210815/0000Z=

以上报文的实际解析区域见 `VAG <https://ds.data.jma.go.jp/svd/vaac/data/VAG/2021/html/20210814_28413000_0016_PF15.html>`_

.. image:: /images/advisory_ash.png

在咨询报文输入框输入咨询报文，可根据初始位置和最终位置的选择，结合情报区的边界，生成对应的图形区域，并自动在模板中填入相应的信息。

低空气象情报模板
"""""""""""""""""""
AIRMET 作为一类不太常发布的报文，这里仅做一个功能上的支持，低空气象情报模板与通用模板类似。

MT OBSC、SFC WIND、VIS、BKN/OVC CLD 之类的天气现象请考虑通过自定义的方式发布。

自定义
^^^^^^^^^^^
如果模板不满足当前的编辑需求，可以尝试使用自定义的方式。

.. image:: /images/sigmet_custom.png

文本框只需要输入报文的正文内容，结尾有无 ``=`` 皆可。

自定义编辑会默认载入上一次发布的同类型报文，取消报会忽略。

删去文本框的内容，会有同类型的 SIGMET 或 AIRMET 模板提示。

.. note:: 通过通知接口传输的 SIGMET 或 AIRMET 报文会在自定义文本框中显示，并在右上角标注来自 API 接口，接收到的报文会在 15 分钟后过期。

取消报
^^^^^^^^^^^
.. image:: /images/sigmet_cancel_template.png

如果有需要取消的报文，可以选择 SIGMET 的序号，对应的取消信息会自动填入。

填入系统中不存在的 SIGMET 序号，取消信息需自行手动输入。

取消信息的结束时间会和报头的结束时间一致。


预览和校验
^^^^^^^^^^^
.. image:: /images/sigmet_preview.png

SIGMET 预览会解析当前要发布的图形区域，显示在画布上。同时，也会对字符进行检查，但不检查逻辑性。

.. image:: /images/sigmet_preview_error.png

如果字符不符合 ASIA/PACIFIC REGIONAL SIGMET GUIDE NINTH EDITION [#apac_sigmet_guide]_ 的规定，出现 **标红字体** 请仔细检查，确认后再发布。


.. [#great_circle] Great Circle https://en.wikipedia.org/wiki/Great_circle
.. [#apac_sigmet_guide] ASIA/PACIFIC REGIONAL SIGMET GUIDE NINTH EDITION https://www.icao.int/APAC/Documents/edocs/APAC-Regional-SIGMET-Guide_9th-Ed.pdf
