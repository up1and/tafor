.. _install:

安装与部署
=================================

安装客户端
----------


编译源码
^^^^^^^^^^^

克隆仓库
"""""""""""""

Tafor 的源码公开在 GitHub, 你可以在这里找到项目的 `介绍 <https://github.com/up1and/tafor>`_。

你可以使用 Git 工具克隆仓库::

    $ git clone git@github.com:up1and/tafor.git

安装依赖
"""""""""""""

首先确保已经正确安装 `Python3`::

    $ pip install -r requirements.txt

安装打包工具 `PyInstaller`::

    $ pip install pyinstaller

Windows 下如何安装 `PyInstaller` 的请参考 `这里 <https://pythonhosted.org/PyInstaller/requirements.html>`_。


编译
"""""""""""""

打包成可执行的 exe 程序，请切换到 :file:`tafor/tafor/` 目录下::

    $ pyinstaller __main__.py -w -F -i icons\icon.ico

打包成功～

.. note:: 打包之前请先在 :file:`tafor/tafor/__init__.py` 文件中注释第 11 行，``BASEDIR = os.path.abspath(os.path.dirname(__file__))``，这是个蠢办法，但有效。

下载发行版
^^^^^^^^^^^
Tafor 的发行版同样放在 GitHub, 你可以在这里 `下载 <https://github.com/up1and/tafor/releases>`_。

发行版依赖
"""""""""""""
- 操作系统需 Windows 7 SP1 或以上
- 遇到缺失 `api-ms-win-crt-runtime-l1-1-0.dll`，请确保安装 `Microsoft Visual C++ 2015 Redistriuutaule`

部署数据源接口
----------------

数据源的接口样例可以在 :file:`tafor/scripts/` 找到。

具体部署方法请参考
`How To Serve Flask Applications with Gunicorn and Nginx on Ubuntu 14.04 <https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-14-04>`_。

.. note:: 不同地方获取数据源的方式不同，所以请根据实际情况更改。

部署电话拨号服务
-----------------

电话服务的样例可参考 `UPSMS <https://github.com/up1and/upsms>`_
