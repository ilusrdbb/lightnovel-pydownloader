# lightnovel-pydownloader

日本轻小说翻译站爬虫导出epub工具，目前已适配esj、轻国、真白萌   
第一次使用请务必读完readme，谢谢  

由于本人未系统的学习过python，基本都是照猫画虎抄来的代码，代码非常的屎请见谅，如果有好的优化建议非常欢迎提pr  
本项目未经过大量测试，如发现bug欢迎提issue，~~至于需求有空再说~~  
**本项目仅供个人学习交流，爬取数据禁止对外传播，禁止用于商业用途，因滥用本项目导致的站点账号异常概不负责**   

## 适配站点
本项目设计初衷仅是用来自用，原则上只适配一手日本轻小说翻译站点  
日轻源站（如hameln）、二手转载站（如哔哩轻小说）、国轻韩轻等站点一般来说将来也不会适配，相关请求适配的issue会直接关闭  
~~tsdm、深夜读书会等适配难度较大的站点大概也不会适配~~

|   站点   |  配置名称  |               特殊情况说明               |
|:------:|:------:|:----------------------------------:|
|  esj   |  esj   |          如挂代理，不能挂日韩节点的代理           |
|  轻之国度  |   lk   |  并非通过网页而是app的api爬取，国内部分地区可能需要挂代理   |
|  真白萌   | masiro | 账密登录暂时需要配置flaresolverr，可选择cookie登录 |
|  百合会   |  yuri  |        一部分特殊格式的文章未适配，不建议使用         |
| 轻小说机翻站 |  fish  |  纯自用，仅支持收藏里直接下载epub，不接受任何相关issue   |

## 关于V2版本
V2版本（2.x.x）不再更新维护，建议迁移至V3版本（3.x.x），V2版本相关的issue也不再受理  
如何迁移：将V3程序（lightnovel.exe）和配置文件（config.yaml，需自行重新更改），覆盖至V2版本根目录中即可

## 使用说明
### Windows
解压release最新版本的压缩包，根据自身需要修改config.yaml配置文件，双击lightnovel.exe运行  
或直接从源码中运行，见下方Linux说明
### Linux
Linux下暂时只能从源代码运行  
安装git和python3，python需要3.11及以上  
安装requirements.txt下依赖  
~~~bash
pip install -r requirements.txt
~~~
下载源代码  
~~~bash
git clone https://github.com/ilusrdbb/lightnovel-pydownloader.git
~~~
根据自身需要修改config.yaml配置文件，运行
~~~bash
python3 lightnovel.py &
~~~

## 一般配置说明
位于程序根目录下config.yaml文件，也可参考文件内注释说明  

|         配置项         |                   说明                    |                                示例                                |
|:-------------------:|:---------------------------------------:|:----------------------------------------------------------------:|
|        site         | 配置需要爬取的站点，支持多站点，可配置项：esj masiro lk yuri |                        ['esj', 'masiro']                         |
|     white_list      |     白名单，程序只爬取白名单内的书籍，支持输入书籍id或书籍地址      | ['1743214829', 'https://www.esjzone.one/detail/1706960711.html'] |
|     login_info      |            登录信息，部分站点支持多种方式登录            |                            见配置文件内注释说明                            |
|     start_page      |       未配置白名单时的爬取范围（包含），收藏或列表开始页数        |                                1                                 |
|      end_page       |       未配置白名单时的爬取范围（包含），收藏或列表结束页数        |                                1                                 |
|      proxy_url      |             代理地址，仅支持http代理              |                     'http://127.0.0.1:1081'                      |
|     is_purchase     |           是否使用轻币或真白萌金币购买付费章节            |                               true                               |
|    max_purchase     |           章节花费上限，高于配置值的章节不购买            |                                20                                |
|    convert_hans     |             是否将标题和内容的繁体转为简体             |                               true                               |
|  scheduler_config   |                 定时执行配置                  |                            见配置文件内注释说明                            |

## 关于高级配置
V3版本将一部分一般用户不需要更改的配置移至高级配置yaml文件中，位于程序根目录下advance.yaml文件，  

|        配置项         |                 说明                 |        示例         |
|:------------------:|:----------------------------------:|:-----------------:|
|      version       |            版本号，非开发者不需修改            | ['esj', 'masiro'] |
|     log_level      |           日志级别，非开发者不需修改            |    INFO或DEBUG     |
|     black_list     |        黑名单，爬取过程中会绕过黑名单配置的书籍        | 类似于白名单white_list  |
|     max_thread     |       线程数，不建议多线程执行，会有ban账号风险       |    最大值8，真白萌强制1    |
|   get_collection   |  是否爬取收藏，如果为false会爬取全站，一般情况下不建议关闭   |       true        |
|      time_out      |               请求超时时间               |        15         |
|     sleep_time     |              每次请求睡眠时间              |    0不睡眠，真白萌强制6    |
|    least_words     |       字数小于此值且无图片的章节不生成epub章节       |       0不限制        |
|    convert_txt     |         是否同时导出txt，未做精细适配慎用         |       false       |
|    push_calibre    |          推送calibre-web设置           |    见配置文件内注释说明     |
|        sign        | 是否开启签到，仅适配轻国和百合会，真白萌由于ban号风险过高不做适配 |       false       |
| download_pic_again |        是否重新下载全部之前爬取失败的图片，慎用        |       false       |
|  clear_pic_table   |          是否清空数据库中的图片信息，慎用          |       false       |
| export_epub_again  |       是否重新导出全部数据库内数据到epub，慎用       |       false       |
|      txt_dir       |         txt保存目录，一般情况下不应修改          |      './txt'      |
|      epub_dir      |         epub保存目录，一般情况下不应修改         |     './epub'      |
|     image_dir      |          图片保存目录，一般情况下不应修改          |    './images'     |
|       domain       |    域名配置，如站点域名变更且本项目未及时更新时可以尝试更改    |                   |
|      xpath配置       |   xpath配置，除非站点页面结构发生改变，一般情况下不应修改   |                   |


## 文件结构说明
如果使用默认配置，程序运行后会在程序目录下生成一系列的文件夹和文件，正常情况不要删除  

|   文件或文件夹名称    |               说明                |
|:-------------:|:-------------------------------:|
|     logs      |              日志文件夹              |
|    images     |   下载插图的文件夹，删除会导致下次导出的epub没有插图   |
|     epub      |            epub保存目录             |
|      txt      | txt保存目录，高级配置中convert_txt开启时才会出现 |
| lightnovel.db |   数据库文件，删除会导致爬取数据全部丢失，千万不要删除    |
|  config.yaml  |              配置文件               |
| advance.yaml  |             高级配置文件              |

## TODO
添加前端ui界面，更方便的修改配置  
真白萌账密登录绕过cf不借助于第三方改用自身程序实现  
代码优化  
