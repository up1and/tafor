.. _interface:

数据接口
=================================

请求
----------
程序会定时对外请求的接口，报文接口请求间隔 1 分钟，情报区接口请求间隔 5 分钟，电话服务接口依据条件触发。

报文接口
^^^^^^^^^^^^^^^^^^^^
请求方式 `HTTP GET`

返回数据如下：

.. code-block:: json

    {
      "FC": "TAF ZJHK 220414Z 220615 04004MPS 6000 BKN007 BKN020 TX22/06Z TN19/15Z=",
      "FT": "TAF ZJHK 220316Z 220606 04004MPS 4000 BR BKN007 BKN020 TX25/06Z TN19/21Z BECMG 0102 BKN015 BKN030=",
      "SA": "METAR ZJHK 220500Z 02004MPS 340V060 8000 BKN007 OVC023 20/19 Q1015 NOSIG="
    }


情报区信息接口
^^^^^^^^^^^^^^^^^^^^^^^
请求方式 `HTTP GET`

返回数据如下：

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
请求方式 `HTTP POST`

认证方式 `HTTP BASIC AUTH`

Python 示例如下：

.. code-block:: python

    requests.post(url, auth=('api', token), data={'mobile': mobile})

- **url** 请求电话拨号服务的地址
- **token** 用于认证用户身份的密钥
- **mobile** 所要呼叫的手机号

.. note:: 认证 Token 需要电话服务网站注册账号后生成。

响应
----------
程序内建了一个 RESTful API 服务，默认启动端口 15400， 可用于验证 TAF、SIGMET、趋势报文的准确性。

TAF 报文验证
^^^^^^^^^^^^^^^^^^^^
地址 ``/api/validate``

请求方式 `HTTP POST`

参数

- **message** 报文内容
- **visHas5000** 能见度有 5000 米
- **cloudHeightHas450** 云高有 450 米
- **weakPrecipitationVerification** 弱降水参与验证

Python 示例如下：

.. code-block:: python

    requests.post('http://127.0.0.1:15400/api/validate',
        data={'visHas5000': 'true', 'message': 'TAF ZJHK 040701Z 0406/0506 06004MPS 6000 TSRA BKN010 FEW023CB BKN033 TX28/0505Z TN24/0418Z BECMG 0407/0408 -SHRA BECMG 0415/0416 BKN030 TEMPO 0410/0414 SHRA='})

返回数据如下

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


趋势报文验证
^^^^^^^^^^^^^^^^^^^^
地址 ``/api/validate``

请求方式 `HTTP POST`

参数

- **message** 报文内容

Python 示例如下：

.. code-block:: python

    requests.post('http://127.0.0.1:15400/api/validate',
        data={'message': 'METAR ZJHK 221100Z 29002MPS 160V330 9999 -TSRA FEW020CB SCT023 24/23 Q1008 RESHRA BECMG FM1111 TL1230 -SHRA='})

返回数据如下

.. code-block:: json

    {
        "html": "METAR ZJHK 221100Z 29002MPS 160V330 9999 -TSRA FEW020CB SCT023 24/23 Q1008 RESHRA<br/>BECMG FM1111 TL1230 -SHRA=",
        "tips": [],
        "pass": true,
        "tokens": [
            [
                "BECMG",
                true
            ],
            [
                "FM1111 TL1230",
                true
            ],
            [
                "-SHRA",
                true
            ]
        ]
    }

SIGMET & AIRMET报文验证
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
SIGMET/AIRMET 报文验证类似，不再做举例。