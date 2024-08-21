# lightnovel-pydownloader

轻小说网站爬虫工具，内置sqlite保存数据，最终生成epub，支持推送到calibre-web服务  
目前已适配真白萌、esj zone、轻国  
本项目基于pycharm开发，开发环境为python 3.9  

## 使用说明
### Windows
解压release最新版本的压缩包，修改config.yaml配置文件，双击lightnovel.exe运行  
或使用Pyinstaller从源代码中打包，环境准备见下方Linux说明  
~~~bash
Pyinstaller lightnovel_exe.spec
~~~
### Linux
Linux下暂时需要从源代码运行  
安装python3环境，建议3.9及以上  
安装requirements.txt下依赖  
~~~bash
pip install -r requirements.txt
~~~
下载源代码  
~~~bash
git clone https://github.com/ilusrdbb/lightnovel-pydownloader.git
~~~
修改config.yaml配置文件，运行
~~~bash
python3 lightnovel.py &
~~~

## 支持站点说明
|站点|配置名称|特殊情况说明|
|:-:|:-:|:-:|
|esj|esj|外链(X)、密码章节(X)|
|轻之国度|lk|gzip解压(√)、bbcode转换(√)、轻币购买(√)、勇者权限(X)、app权限(√)|
|真白萌|masiro|cf盾(√)、等级权限(X)、金币购买(√)|

## 配置说明
配置文件位于程序目录下的config.yaml，运行程序请根据自身需要修改配置
|配置项|说明|
|:-:|:-:|
|site|配置需要爬取的站点，默认值esj，masiro 真白萌、esj esj、lk 轻国，输入all为爬取全部支持的站点|
|white_list|白名单，数组，esj和真白萌填入书籍的地址，轻国填入合集的id（数字不是字符串），不支持轻国单本id|
|black_list|黑名单，数组，esj和真白萌填入书籍的地址，轻国填入单本或合集的id（数字不是字符串）|
|max_thread|最大线程数，默认值1，不建议设置过大，程序限制esj最大值8、轻国最大值4、真白萌最大值1|
|login_info|登录账号密码，必填，目前支持的站点都必须登录才可爬取|
|flaresolverr_url|flaresolverr服务地址，用于绕过真白萌cf盾，例：http://127.0.0.1:8191/v1，目前只有此镜像可以完美绕过alexfozor/flaresolverr:pr-1300|
|get_collection|是否爬取收藏页，默认值false，如选否则爬取网站日轻列表|
|start_page|爬取范围（包含），收藏或列表开始页数，默认值1|
|end_page|爬取范围（包含），收藏或列表结束页数，默认值1|
|proxy_url|代理地址，仅支持http代理，例：http://127.0.0.1:1081，esj只能使用非日韩的代理，真白萌代理只对下载图片生效|
|is_purchase|是否使用轻币或真白萌金币购买付费章节，默认值false|
|max_purchase|消费上限，超过此值的章节不购买，默认值20|
|time_out|请求超时时间（秒），默认值15|
|sleep_time|每次网络请求睡眠时间（秒），默认值1，设置为0时不限制，例：设置2为随机睡0~2秒，注意真白萌此配置项无效程序会强制睡10秒防止频繁请求报错|
|least_words|html字节数小于此值且不存在图片的章节不生成epub，默认值0，设置为0时不限制|
|convert_hans|生成epub是否将标题和内容的繁体转为简体，默认值true|
|scheduler_config|配置每天定时执行爬虫任务，注意如果爬真白萌很可能一天爬不完，此时不建议开启定时执行|
|push_calibre|配置docker版calibre-web推送|
|epub_dir|epub保存目录，默认值./epub，不建议更改|
|image_dir|图片保存目录，默认值./images，不建议更改|
|download_fail_again|是否统一下载之前爬取失败的图片（优先级1），默认值false，定时开启时此项无效，此项开启时正常爬虫任务会停止|
|delete_pic_table|是否清空数据库中的图片信息（优先级2），默认值false，此配置只应该在误删图片保存目录的时候开启，定时开启时此项无效，此项开启时正常爬虫任务会停止|
|purchase_again|是否统一支付之前未支付的章节（优先级3），默认值false，定时开启时此项无效，此项开启时正常爬虫任务会停止|
|export_epub_again|是否导出数据库数据到epub（优先级4），默认值false，定时开启时此项无效，此项开启时正常爬虫任务会停止|
|url_config|网站地址配置，请勿更改|
|xpath_config|xpath配置，请勿更改|

## 文件结构说明
如果使用默认配置，程序运行后会在程序目录下生成一系列的文件，正常情况不要删除这些文件  
|文件或文件夹名称|说明|
|:-:|:-:|
|logs|日志文件夹，可以删除|
|images|下载插图的文件夹，删除会导致epub无插图，勿删|
|epub|epub保存目录|
|lightnovel.db|数据库文件，删除会导致爬取数据丢失，勿删|
|config.yaml|配置文件，勿删|

## 须知
由于本人未系统的学习过python，基本都是照猫画虎抄来的代码，代码非常的屎请见谅  
本项目未经过大量测试，如发现bug欢迎提issue，~~至于需求有空再说~~  
**本项目仅供个人学习交流，爬取数据不得对外传播，不得用于商业用途**   

## TODO
添加百合会支持  
