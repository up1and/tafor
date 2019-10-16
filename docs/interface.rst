.. _interface:

数据接口
=================================

请求
----------
程序会定时对外请求的接口，报文接口请求间隔 1 分钟，情报区接口请求间隔 5 分钟，电话服务接口依据条件触发。

各类请求地址可以在 设置 -> 数据源 中更改，详情请参考 :ref:`guide`。

报文接口
^^^^^^^^^^^^^^^^^^^^
.. code-block:: http

    GET <latest_message_url> HTTP/1.1

**latest_message_url** 当前机场最新的报文数据接口

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

.. note:: 如果需要查询 SIGMET 或 AIRMET 报文，要以列表形式返回有效期内此类型所有的报文，类型键值可选 ``WS WC WV WA``。

情报区信息接口
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: http

    GET <fir_information_url> HTTP/1.1

**fir_information_url** 当前情报区的信息接口

需返回以下数据：

.. code-block:: json

    {
      "boundaries": [], 
      "layers": [
        {
        "coordinates": [
            [
            105, 
            25
            ], 
            [
            120, 
            10
            ]
        ], 
        "image": "https://tafor.herokuapp.com/static/cloud.jpg", 
        "name": "Himawari 8", 
        "rect": [
            15, 
            50, 
            260, 
            260
        ], 
        "size": [
            376, 
            376
        ], 
        "updated": "Mon, 30 Jul 2018 21:33:00 GMT"
        }
      ]
    }


- **boundaries** 情报区的边界，用一组点表示，顺时针排列
- **layers** 由数组组成的图层信息，每层都需要包含以下内容
    - **coordinates** 卫星云图的经纬度坐标范围，标记左上角到右下角两个点，用十进制经度，纬度表示
    - **image** 当前时刻最新的卫星云图地址
    - **name** 图层名称
    - **rect** SIGMET 编辑区域显示的区域大小和位置，前两个参数表示区域的起始点 x、y，后两个参数表示区域的宽和高，单位像素
    - **size** 卫星云图的宽和高，单位像素
    - **updated** 卫星云图更新的时间，世界时

.. note:: 无法获取最新的底图时，``image`` 和 ``updated`` 的值要标记为 ``null``，这样程序才会继续启用画布功能，并绘制一个灰色纯色底图。


电话服务接口
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: http

    POST <call_service_url> HTTP/1.1
    Authorization: Basic <auth>

**call_service_url** 请求电话拨号服务的地址

**auth** 用于认证用户身份的密钥，生成方式为 ``base64('api':token)``

参数：

- **mobile** 所要呼叫的手机号

.. note:: 认证 token 需要电话服务网站注册账号后生成，可以在 设置 -> 电话服务 中更改相关设置。

响应
----------
程序内建了一个 RESTful API 服务，默认启动端口 9407， 可用于验证 TAF、SIGMET、趋势报文的准确性，以及告知程序正在编辑的观测报文。

TAF 报文验证
^^^^^^^^^^^^^^^^^^^^

.. code-block:: http

    GET /api/validate HTTP/1.1

参数：

- **message** 报文内容

示例：

.. code-block:: text

    message=TAF ZJHK 040701Z 0406/0506 06004MPS 6000 TSRA BKN010 FEW023CB BKN033 TX28/0505Z TN24/0418Z BECMG 0407/0408 -SHRA BECMG 0415/0416 BKN030 TEMPO 0410/0414 SHRA=

返回数据：

.. code-block:: json

    {
        "pass": false,
        "tips": [
            "阵性降水应包含 CB"
        ],
        "html": "TAF ZJHK 040701Z 0406/0506 06004MPS 6000 TSRA BKN010 FEW023CB BKN033 TX28/0505Z TN24/0418Z<br/>BECMG 0407/0408 -SHRA<br/>BECMG 0415/0416 <span style=\"color: red\">BKN030</span><br/>TEMPO 0410/0414 SHRA=",
        "tokens": [
            [
                "TAF",
                true
            ],
            [
                "ZJHK",
                true
            ],
            [
                "040701Z",
                true
            ],
            [
                "0406/0506",
                true
            ],
            [
                "06004MPS",
                true
            ],
            [
                "6000",
                true
            ],
            [
                "TSRA",
                true
            ],
            [
                "BKN010 FEW023CB BKN033",
                true
            ],
            [
                "TX28/0505Z TN24/0418Z",
                true
            ],
            [
                "BECMG",
                true
            ],
            [
                "0407/0408",
                true
            ],
            [
                "-SHRA",
                true
            ],
            [
                "BECMG",
                true
            ],
            [
                "0415/0416",
                true
            ],
            [
                "BKN030",
                false
            ],
            [
                "TEMPO",
                true
            ],
            [
                "0410/0414",
                true
            ],
            [
                "SHRA",
                true
            ]
        ]
    }

.. note:: 校验的阈值如云高是否有 450 米或能见度是否有 5000 米可以在 设置 -> 校验 中更改，趋势校验也是如此，详情请参考 :ref:`guide`。

趋势报文验证
^^^^^^^^^^^^^^^^^^^^

.. code-block:: http

    GET /api/validate HTTP/1.1

参数：

- **message** 报文内容

示例：

.. code-block:: text

    message=METAR ZJHK 221100Z 29002MPS 160V330 9999 -TSRA FEW020CB SCT023 24/23 Q1008 RESHRA BECMG TL1230 -SHRA=

返回数据：

.. code-block:: json

    {
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

SIGMET & AIRMET 报文验证
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
SIGMET/AIRMET 报文验证类似，不再做举例。


显示观测报文
^^^^^^^^^^^^^^^^^^^^

.. code-block:: http

    POST /api/notifications HTTP/1.1
    Authorization: Bearer VGhlIFZveWFnZSBvZiB0aGUgTW9vbg==

参数：

- **message** 报文内容

示例：

.. code-block:: text

    message=METAR ZJHK 210600Z 26002MPS 200V300 9999 BKN030 36/27 Q1004 NOSIG=

返回数据：

.. code-block:: json

    {
        "message": "METAR ZJHK 210600Z 26002MPS 200V300 9999 BKN030 36/27 Q1004 NOSIG=",
        "created": "Fri, 21 Jun 2019 05:57:34 GMT"
    }


显示 SIGMET/AIRMET 报文
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: http

    POST /api/notifications HTTP/1.1
    Authorization: Bearer VGhlIFZveWFnZSBvZiB0aGUgTW9vbg==

参数：

- **message** 报文内容

示例：

.. code-block:: text

    message=ZJSA SIGMET 1 VALID 300755/301155 ZJHK- ZJSA SANYA FIR EMBD TS OBS AT 0115Z WI N1906 E11150 - N1731 E10815 - N1904 E10702 - N2030 E10802 - N2030 E11130 - N1930 E11130 - N1906 E11150 TOP FL300 MOV N 20KMH NC=

返回数据：

.. code-block:: json

    {
        "message": "ZJSA SIGMET 1 VALID 300755/301155 ZJHK- ZJSA SANYA FIR EMBD TS OBS AT 0115Z WI N1906 E11150 - N1731 E10815 - N1904 E10702 - N2030 E10802 - N2030 E11130 - N1930 E11130 - N1906 E11150 TOP FL300 MOV N 20KMH NC=",
        "created": "Sun, 30 Jun 2019 07:49:37 GMT"
    }


.. note:: Bearer Token 默认值为 `VGhlIFZveWFnZSBvZiB0aGUgTW9vbg==`，可在 关于 -> 令牌 中查看，程序运行目录命令行下输入 ``tafor token --generate`` 可用于重新生成令牌，建议在初次设置后重新生成令牌。
