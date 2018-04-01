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

.. note:: 不同地方获取数据源的方式不同，所以请根据实际情况更改。

下面用一个简单的例子来说明如何在 Ubuntu 14.04 部署 Flask 应用。

安装依赖
^^^^^^^^^^^^^^^^^^^^^^^^^^
安装 `Nginx` 和 `Supervisor` 以及所需的一些依赖::

    $ sudo apt install nginx supervisor
    $ sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev xz-utils tk-dev


安装 `pyenv` & `pyenv-virtualenv`::

    $ git clone https://github.com/pyenv/pyenv.git ~/.pyenv
    $ git clone https://github.com/pyenv/pyenv-virtualenv.git ~/.pyenv/plugins/pyenv-virtualenv
    $ echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
    $ echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
    $ echo 'eval "$(pyenv init -)"' >> ~/.bashrc
    $ exec $SHELL

安装 `Python`::

    $ pyenv install 3.6.1

把 :file:`tafor/scripts/` 目录下的文件放入 :file:`/var/www/tafor_api` 目录下，
创建虚拟环境并安装依赖::

    $ cd /var/www/tafor_api
    $ pyenv virtualenv 3.6.1 tafor_api
    $ pyenv activate tafor_api
    $ pip install -r requirements.txt


测试启动 Flask 应用
^^^^^^^^^^^^^^^^^^^^^^
我们通过 `Gunicorn` 来启动 Flask，你也可以使用 `uwsgi`::

    $ gunicorn --bind 0.0.0.0:8000 tafor:app

如果你能通过本机 IP 地址加端口 `:8000` 访问网页，则应用没有问题。


使用 Supervisor 守护进程
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`Supervisor` 是一个进程守护软件，我们通过它来启动 Flask 程序，你也可以使用 `Upstart`、 `Systemd` 等。

创建配置文件::

    $ sudo vi /etc/supervisor/conf.d/tafor_api.conf


写入配置::

    [program:tafor_api]
    environment = TAFOR_API_ENV=prod
    command = /home/user/.pyenv/versions/tafor_api/bin/gunicorn tafor:app --workers 1 --bind unix:tafor_api.sock -m 007
    directory = /var/www/tafor_api
    user = root
    startsecs = 0
    stopwaitsecs = 0
    autostart = true
    autorestart = true


.. note:: 请注意把 `user` 替换为实际用户所在的地址。


生效配置::

    $ sudo service supervisor restart


使用 Nginx 代理请求
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
我们需要通过 `Nginx` 把请求转发到 `tafor_api.sock` 文件上，

创建配置文件::

    $ sudo vi /etc/nginx/sites-available/tafor_api

写入配置::

    upstream tafor_api {
        server unix:///var/www/tafor_api/tafor_api.sock fail_timeout=0;
    }


    server {

        listen 6575;
        listen [::]:6575;

        access_log    /var/log/nginx/tafor_api_access.log;  
        error_log    /var/log/nginx/tafor_api_error.log;  

        root /var/www/tafor_api;

        location / {
            proxy_pass http://tafor_api;
            proxy_set_header Host $host:$server_port;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

    }

生效配置::

    $ sudo ln -s /etc/nginx/sites-available/tafor_api /etc/nginx/sites-enabled
    $ sudo service nginx restart


.. note:: 如果是第一次安装使用 Nginx 或者重启 Nginx 服务之后 localhost 还是显示默认欢迎页面，请删除 /etc/nginx/sites-enabled/default 文件。


部署电话拨号服务
-----------------

`UPSMS <https://github.com/up1and/upsms>`_ 的部署方式和数据源类似，先使用 `Gunicorn` 启动应用，再用 `Nginx` 代理请求，不过这里需额外启动监听电话模块的脚本。

创建配置文件::

    $ sudo vi /etc/supervisor/conf.d/upsms_modem

写入配置::

    [program:upsms_modem]
    command = /home/user/.pyenv/versions/upsms/bin/python manage.py modem
    directory = /var/www/upsms
    user = root
    startsecs = 0
    stopwaitsecs = 0
    autostart = true
    autorestart = true

生效配置::

    $ sudo service supervisor restart


其他部署方法请参考
`How To Serve Flask Applications with Gunicorn and Nginx on Ubuntu 14.04 <https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-14-04>`_。

部署的方式有多种，这只是其中一些例子，你也可以选择更好用的 `Docker <https://www.docker.com/>`_ 部署 Flask 应用。
