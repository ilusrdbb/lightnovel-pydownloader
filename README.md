# lightnovel-pydownloader

[![Stars](https://img.shields.io/github/stars/ilusrdbb/lightnovel-pydownloader)](https://github.com/ilusrdbb/lightnovel-pydownloader) [![License](https://img.shields.io/github/license/ilusrdbb/lightnovel-pydownloader)](LICENSE) [![Release](https://img.shields.io/github/v/release/ilusrdbb/lightnovel-pydownloader)](https://github.com/ilusrdbb/lightnovel-pydownloader/releases)

日本轻小说翻译站爬虫导出 epub 工具  

> [!NOTE]
> 第一次使用请务必完整阅读本README  
> 提交bug的issue请附上日志，且至少告知基本的运行配置（如站点、书籍id等）  

> [!WARNING]
> 本项目仅供个人学习交流使用，下载的内容版权归原作者/出版社所有  
> 禁止对外传播，禁止用于商业用途，因滥用本项目导致的站点账号异常概不负责  

本项目经历过多次迭代重构，但是我依旧认为目前的代码非常的屎，如果有好的优化建议欢迎提交pr   
由于本人能力有限，目前少量后端以及几乎全部的GUI前端代码由AI生成  

## 功能特性

- 多站点支持：esj、轻之国度、真白萌、百合会、轻小说机翻站
- 支持从完整列表、收藏列表、指定单本导出 epub，且支持同时导出 txt
- 额外支持代理、定时执行、繁转简、calibre-web推送等功能
- 提供 CLI（`lightnovel.exe`）与 GUI（`lightnovel-gui.exe`）两种运行方式

## 适配站点

本项目设计初衷仅用于自用，原则上只适配一手日本轻小说翻译站点  
拒绝适配二手转载站（如哔哩轻小说）、国轻韩轻等站点，相关请求适配的 issue 会直接关闭  

|     站点     | 配置名称 |                            特殊情况说明                             |
|:------------:|:--------:|:-------------------------------------------------------------------:|
|     esj      |   esj    |                   如挂代理，不能挂日韩节点的代理                    |
|   轻之国度   |    lk    |                    新轻国源站未稳定，不建议使用                     |
|    真白萌    |  masiro  | 账密登录需要使用系统安装的 Chrome 浏览器绕过 cf，可选择 cookie 登录 |
|    百合会    |   yuri   |        需要使用系统安装的 Chrome 浏览器绕过 waf，不建议使用         |
| 轻小说机翻站 |   fish   |      纯自用，仅支持从收藏里直接下载 epub，不接受任何相关 issue      |

## 使用说明

### Windows

解压 release 最新版本的压缩包，双击 `lightnovel-gui.exe`（带 UI 界面）或手动修改配置文件后 `lightnovel.exe`（原 CLI 方式）运行  
如果想直接从源码运行，见下方 Linux 说明  

### Linux

Linux 下暂时只能以CLI方式从源代码运行  
安装 git 和 python3，Python 需要 3.11（建议 3.12）  

```bash
# 下载源代码
git clone https://github.com/ilusrdbb/lightnovel-pydownloader.git
cd lightnovel-pydownloader

# 安装依赖
pip install -r requirements.txt
```

根据自身需要修改 `config.yaml` 和 `advance.yaml` 配置文件，然后以后台方式运行  

```bash
nohup python lightnovel.py > /dev/null 2>&1 &
```

### 更新

覆盖新版本的 `lightnovel.exe` 和 `lightnovel-gui.exe` 即可  

### 关于 V2 版本

V2 版本（2.x.x）不再更新维护，建议迁移至 V3 版本（3.x.x），V2 版本相关的 issue 不再受理  
迁移方法：将 V3 程序（`lightnovel.exe` 和 `lightnovel-gui.exe`）和配置文件（`config.yaml` 和 `advance.yaml`，需自行重新更改）覆盖至 V2 版本根目录中即可  

## 配置项说明

### 一般配置

位于程序根目录下 `config.yaml` 文件，也可参考文件内注释说明  

|      配置项      |                             说明                             |                           示例                            |
|:----------------:|:------------------------------------------------------------:|:---------------------------------------------------------:|
|       site       | 配置需要爬取的站点，支持多站点，可配置项：esj masiro lk yuri |                     ['esj', 'masiro']                     |
|    white_list    | 白名单，程序只爬取白名单内的书籍，支持输入书籍 id 或书籍地址 | ['114514', 'https://www.esjzone.one/detail/1919810.html'] |
|    login_info    |              登录信息，部分站点支持多种方式登录              |                   见配置文件内注释说明                    |
|    start_page    |     未配置白名单时的爬取范围（包含），收藏或列表开始页数     |                             1                             |
|     end_page     |     未配置白名单时的爬取范围（包含），收藏或列表结束页数     |                             1                             |
|    proxy_url     |                  代理地址，仅支持 http 代理                  |                  'http://127.0.0.1:1081'                  |
|   is_purchase    |                是否使用真白萌金币购买付费章节                |                           true                            |
|   max_purchase   |             章节花费上限，高于配置值的章节不购买             |                            20                             |
|   convert_hans   |                是否将标题和内容的繁体转为简体                |                           true                            |
| scheduler_config |                         定时执行配置                         |                   见配置文件内注释说明                    |

### 高级配置

V3 版本将一部分一般用户不需要更改的配置移至高级配置文件，位于程序根目录下 `advance.yaml` 文件  

|       配置项        |                                  说明                                  |          示例           |
|:-------------------:|:----------------------------------------------------------------------:|:-----------------------:|
|      log_level      |                       日志级别，非开发者不需修改                       |      INFO 或 DEBUG      |
|     black_list      |                黑名单，爬取过程中会绕过黑名单配置的书籍                | 类似于白名单 white_list |
|     max_thread      |              线程数，不建议多线程执行，会有 ban 账号风险               | 最大值 8，真白萌强制 1  |
|   get_collection    |      是否爬取收藏，如果为 false 会爬取全站，一般情况下不建议关闭       |          true           |
|      time_out       |                              请求超时时间                              |           15            |
|     sleep_time      |                            每次请求睡眠时间                            | 0 不睡眠，真白萌强制 6  |
|     least_words     |               字数小于此值且无图片的章节不生成 epub 章节               |        0 不限制         |
|     convert_txt     |                            是否同时导出 txt                            |          false          |
| convert_txt_chapter |                  是否同时导出 txt 且按照章节分割 txt                   |          false          |
|    push_calibre     |                         推送 calibre-web 设置                          |  见配置文件内注释说明   |
|        sign         |  是否开启签到，仅适配轻国和百合会，真白萌由于 ban 号风险过高不做适配   |          false          |
| download_pic_again  |                是否重新下载全部之前爬取失败的图片，慎用                |          false          |
|   clear_pic_table   |                    是否清空数据库中的图片信息，慎用                    |          false          |
|  export_epub_again  |               是否重新导出全部数据库内数据到 epub，慎用                |          false          |
|       txt_dir       |                    txt 保存目录，一般情况下不应修改                    |         './txt'         |
|      epub_dir       |                   epub 保存目录，一般情况下不应修改                    |        './epub'         |
|      image_dir      |                    图片保存目录，一般情况下不应修改                    |       './images'        |
|       domain        |        域名配置，如站点域名变更且本项目未及时更新时可以尝试更改        |                         |
|         ua          | 浏览器 user-agent，如果正确抓取 cookie 但是依旧无法登录可能需要更新 ua |                         |
|    esj_book_pwd     |              esj 书籍密码配置，格式：书籍或章节 id: 密码               |    114514: '1919810'    |
|     xpath 配置      |        xpath 配置，除非站点页面结构发生改变，一般情况下不应修改        |                         |

## 文件结构说明

程序默认或运行后在程序目录下有一系列的文件夹和文件，除logs外正常情况都不应删除  

|  文件或文件夹名称  |                         说明                         |
|:------------------:|:----------------------------------------------------:|
|        logs        |                      日志文件夹                      |
|       images       | 下载插图的文件夹，删除会导致下次导出的 epub 没有插图 |
|        epub        |                    epub 保存目录                     |
|        txt         | txt 保存目录，高级配置中 convert_txt 开启时才会出现  |
|   lightnovel.db    |        数据库文件，删除会导致爬取数据全部丢失        |
|    config.yaml     |                       配置文件                       |
|    advance.yaml    |                     高级配置文件                     |
|   lightnovel.exe   |                主程序（原 CLI 方式）                 |
| lightnovel-gui.exe |                 主程序（带 UI 界面）                 |

## TODO

- 优化 epub 导出
- 更好更易维护的异常处理
- 测试用例
