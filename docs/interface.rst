.. _interface:

数据接口
=================================

请求
----------
Tafor 会定时对外轮询数据，报文接口请求间隔为 1 分钟，情报区接口请求间隔为 2 分钟。

各类请求地址可以在 设置 -> 接口 中更改，详情请参考 :ref:`guide`。

请求接口使用 Vercel 创建样例，这里以 https://tafor-script.vercel.app 为例，实际地址以当前生产环境为准。

报文接口
^^^^^^^^^^^^^^^^^^^^
.. code-block:: http

    GET https://tafor-script.vercel.app/messages/<airport> HTTP/1.1

**airport** 机场的 ICAO 四字代码

需返回以下数据：

.. code-block:: json

    {
      "FC": "TAF ZJHK 220414Z 2206/2215 04004MPS 6000 BKN007 BKN020 TX22/2206Z TN19/2215Z=",
      "FT": "TAF ZJHK 220316Z 2206/2306 04004MPS 4000 BR BKN007 BKN020 TX25/2206Z TN19/2221Z BECMG 2301/2302 SCT020=",
      "SA": "METAR ZJHK 220500Z 02004MPS 340V060 8000 BKN007 OVC023 20/19 Q1015 NOSIG=",
      "WS": [
        "ZJSA SIGMET 2 VALID 220135/150535 ZJHK- ZJSA SANYA FIR EMBD TS FCST WI N2030 E11043 - N1830 E11025 - N1812 E10817 - N1951 E10749 - N1957 E10755 - N2030 E10802 - N2030 E11043 TOP FL450 MOV S 20KMH NC", 
        "ZJSA SIGMET 3 VALID 220530/220930 ZJHK- ZJSA SANYA FIR EMBD TS FCST WI N1913 E10801 - N1923 E11001 - N1815 E11012 - N1804 E10821 - N1913 E10801 TOP FL430 STNR WKN"
      ]
    }

.. note:: SIGMET 或 AIRMET 报文，会以列表形式返回有效期内此类型所有的报文，类型键值可选 ``WS WC WV WA``。

图层接口
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: http

    GET https://tafor-script.vercel.app/layers HTTP/1.1

需返回以下结构的数据：

.. code-block:: json

    [
        {
            "extent": [
                98,
                0,
                137,
                30
            ],
            "image": "https://tafor-script.vercel.app/static/clouds/ir_clouds.webp",
            "name": "Himawari IR Clouds",
            "overlay": "standalone",
            "proj": "+proj=longlat +ellps=WGS84",
            "updated": "Sun, 16 Oct 2022 06:53:52 GMT"
        },
        {
            "extent": [
                98,
                0,
                137,
                30
            ],
            "image": "https://tafor-script.vercel.app/static/clouds/true_color.webp",
            "name": "Himawari True Color",
            "overlay": "standalone",
            "proj": "+proj=longlat +ellps=WGS84",
            "updated": "Sun, 16 Oct 2022 06:53:52 GMT"
        },
        {
            "extent": [
                104.355556,
                14.159722,
                115.215833,
                24.128611
            ],
            "image": "https://tafor-script.vercel.app/static/echos/sanya_fir_mosaic.png",
            "name": "Sanya FIR Mosaic",
            "overlay": "mixed",
            "proj": "+proj=longlat +ellps=WGS84",
            "updated": "Sun, 16 Oct 2022 06:53:52 GMT"
        }
    ]


图层信息由一组或多组数据成，每层都需要包含以下结构：

- **extent** 图层的坐标范围，使用经纬度表示，`minx, miny, maxx, maxy`
- **image** 图层的地址
- **name** 图层名称
- **overlay** 参数两个选项，`standalone` 和 `mixed`，`mixed` 表示图层可以和其他图层叠加，`standalone` 只能单独存在。
- **proj** 图层投影信息，需要和设置的一致，才能正确加载
- **updated** 图层更新的时间，世界时

.. note:: 无法获取最新的底图时，``image`` 和 ``updated`` 的值标记为 ``null``。


响应
----------
程序内建了一个 RESTful API 服务，默认启动端口 9407， 用于接收外部程序发送的报文，支持接收观测报文和 SIGMET。

以下示例使用的 Bearer Token 为 ``VGhlIFZveWFnZSBvZiB0aGUgTW9vbg==``。


显示观测报文和校验
^^^^^^^^^^^^^^^^^^^^

.. code-block:: http

    POST /api/notifications HTTP/1.1
    Authorization: Bearer VGhlIFZveWFnZSBvZiB0aGUgTW9vbg==

参数：

- **message** 报文内容
- **validation** 是否启用验证，可选项，默认不启用

通知示例：

.. code-block:: text

    message=METAR%20ZJHK%20210600Z%2026002MPS%20200V300%209999%20BKN030%2036%2F27%20Q1004%20NOSIG%3D

返回数据：

.. code-block:: json

    {
        "message": "METAR ZJHK 210600Z 26002MPS 200V300 9999 BKN030 36/27 Q1004 NOSIG=",
        "created": "Fri, 21 Jun 2019 05:57:34 GMT"
    }

创建成功返回 HTTP Created 201 状态码，数据里面会有一个接口接收通知的时间。 

此时接口用于通知预报软件未来要发的观测报文。

通知和验证示例:

.. code-block:: text

    message=METAR%20ZJHK%20221100Z%2029002MPS%20160V330%209999%20-TSRA%20FEW020CB%20SCT023%2024%2F23%20Q1008%20RESHRA%20BECMG%20TL1230%20-SHRA%3D&validation=on

返回数据：

.. code-block:: json

    {
        "message": "METAR ZJHK 221100Z 29002MPS 160V330 9999 -TSRA FEW020CB SCT023 24/23 Q1008 RESHRA BECMG TL1230 -SHRA=",
        "created": "Fri, 21 Jun 2019 05:58:34 GMT",
        "validations":{
            "html": "METAR ZJHK 221100Z 29002MPS 160V330 9999 -TSRA FEW020CB SCT023 24/23 Q1008 RESHRA<br/>BECMG TL1230 -SHRA=",
            "tips": [],
            "pass": true,
            "tokens": [
                [
                    "BECMG",
                    true
                ],
                [
                    "TL1230",
                    true
                ],
                [
                    "-SHRA",
                    true
                ]
            ]
        }
    }

参数 validation 支持以下字符

.. code-block:: python

    TRUE_STRINGS = ('true', 'True', 't', 'yes', 'y', '1', 'on')
    FALSE_STRINGS = ('false', 'False', 'f', 'no', 'n', '0', 'off')

开启验证后，返回数据会多一个 validations 字段，其中:

- **html** 报文的 html 版本，趋势预报有错的位置会高亮显示
- **tips** 列表，文字提示信息，无错不显示
- **pass** 趋势预报是否校验通过
- **tokens** 趋势项单独拆解，并标注出错项

观测软件趋势验证可以参考如下逻辑，点击编报按钮后，观测软件会请求访问这个接口，如果接口告知观测软件趋势校验通过，不做任何改变。 如果没有通过，自动把趋势改为 NOSIG=。

.. note:: 在传递 message 参数时，如果是通过 query params 传递时，一定要 encode uri，因为 +TSRA 中的 + 符号会被转义为空格，如果是用 JSON 附加在请求 body 上，则不需要。

显示 SIGMET/AIRMET 报文
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: http

    POST /api/notifications HTTP/1.1
    Authorization: Bearer VGhlIFZveWFnZSBvZiB0aGUgTW9vbg==

参数：

- **message** 报文内容

示例：

.. code-block:: text

    message=ZJSA%20SIGMET%201%20VALID%20300755%2F301155%20ZJHK-%20ZJSA%20SANYA%20FIR%20EMBD%20TS%20OBS%20AT%200115Z%20WI%20N1906%20E11150%20-%20N1731%20E10815%20-%20N1904%20E10702%20-%20N2030%20E10802%20-%20N2030%20E11130%20-%20N1930%20E11130%20-%20N1906%20E11150%20TOP%20FL300%20MOV%20N%2020KMH%20NC%3D

返回数据：

.. code-block:: json

    {
        "message": "ZJSA SIGMET 1 VALID 300755/301155 ZJHK- ZJSA SANYA FIR EMBD TS OBS AT 0115Z WI N1906 E11150 - N1731 E10815 - N1904 E10702 - N2030 E10802 - N2030 E11130 - N1930 E11130 - N1906 E11150 TOP FL300 MOV N 20KMH NC=",
        "created": "Sun, 30 Jun 2019 07:49:37 GMT"
    }

